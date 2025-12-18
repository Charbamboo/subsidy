"""
メイン処理
Flaskアプリケーションの定義と実行
"""

from flask import Flask, render_template, request, jsonify
from .config import (
    FLASK_HOST,
    FLASK_PORT,
    FLASK_DEBUG,
    TARGET_AREAS,
    EMPLOYEE_COUNTS,
    USE_PURPOSES,
    SORT_FIELDS,
    SORT_ORDERS
)
from .api_client import JGrantsApiClient, ApiClientError, format_subsidy_amount
from .local_data import LocalSubsidySearcher


def create_app() -> Flask:
    """
    Flaskアプリケーションを作成

    Returns:
        Flask: 設定済みのFlaskアプリケーション
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )

    api_client = JGrantsApiClient()
    local_searcher = LocalSubsidySearcher()

    @app.route("/")
    def index():
        """
        トップページ（検索フォーム）を表示
        """
        return render_template(
            "index.html",
            target_areas=TARGET_AREAS,
            employee_counts=EMPLOYEE_COUNTS,
            use_purposes=USE_PURPOSES,
            sort_fields=SORT_FIELDS,
            sort_orders=SORT_ORDERS,
            local_data_count=len(local_searcher.subsidies)
        )

    @app.route("/search", methods=["POST"])
    def search():
        """
        補助金を検索してJSON形式で結果を返す
        APIとローカルデータの両方を検索
        """
        try:
            # フォームデータの取得
            keyword = request.form.get("keyword", "").strip()
            sort = request.form.get("sort", "created_date").strip()
            order = request.form.get("order", "DESC").strip()
            acceptance = "1" if request.form.get("acceptance_only") == "on" else "0"
            target_area = request.form.get("target_area", "").strip() or None
            target_number_of_employees = request.form.get("target_number_of_employees", "").strip() or None
            use_purpose = request.form.get("use_purpose", "").strip() or None
            
            # データソースの選択
            search_jgrants = request.form.get("search_jgrants", "on") == "on"
            search_local = request.form.get("search_local", "on") == "on"

            # キーワードのバリデーション（2文字以上必須）
            if not keyword or len(keyword) < 2:
                return jsonify({
                    "success": False,
                    "error": "検索キーワードは2文字以上で入力してください"
                }), 400

            formatted_subsidies = []
            api_count = 0
            local_count = 0
            api_error = None

            # Jグランツ API検索
            if search_jgrants:
                try:
                    result = api_client.search_subsidies(
                        keyword=keyword,
                        sort=sort,
                        order=order,
                        acceptance=acceptance,
                        target_area=target_area,
                        target_number_of_employees=target_number_of_employees,
                        use_purpose=use_purpose
                    )

                    subsidies = result.get("result", [])
                    api_count = result.get("metadata", {}).get("resultset", {}).get("count", 0)

                    for subsidy in subsidies:
                        formatted_subsidies.append({
                            "id": subsidy.get("id", ""),
                            "name": subsidy.get("name", ""),
                            "title": subsidy.get("title", ""),
                            "target_area": subsidy.get("target_area_search", ""),
                            "subsidy_max_limit": format_subsidy_amount(subsidy.get("subsidy_max_limit")),
                            "subsidy_max_limit_raw": subsidy.get("subsidy_max_limit"),
                            "acceptance_start": subsidy.get("acceptance_start_datetime", ""),
                            "acceptance_end": subsidy.get("acceptance_end_datetime", ""),
                            "target_employees": subsidy.get("target_number_of_employees", ""),
                            "source": "Jグランツ",
                            "status": ""
                        })
                except ApiClientError as e:
                    api_error = str(e)

            # ローカルデータ検索
            if search_local:
                local_results = local_searcher.search(
                    keyword=keyword,
                    target_area=target_area,
                    acceptance_only=(acceptance == "1")
                )
                local_count = len(local_results)

                for subsidy in local_results:
                    formatted_subsidies.append(local_searcher.format_for_display(subsidy))

            total_count = api_count + local_count

            return jsonify({
                "success": True,
                "count": total_count,
                "api_count": api_count,
                "local_count": local_count,
                "api_error": api_error,
                "subsidies": formatted_subsidies
            })

        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"予期しないエラーが発生しました: {str(e)}"
            }), 500

    @app.route("/detail/<subsidy_id>")
    def detail(subsidy_id: str):
        """
        補助金の詳細情報を取得
        """
        try:
            # ローカルデータの場合
            if subsidy_id.startswith("local_"):
                subsidy = local_searcher.get_by_id(subsidy_id)
                if subsidy:
                    return jsonify({
                        "success": True,
                        "subsidy": local_searcher.format_detail_for_display(subsidy)
                    })
                else:
                    return jsonify({
                        "success": False,
                        "error": "補助金が見つかりませんでした"
                    }), 404

            # Jグランツ APIの場合
            result = api_client.get_subsidy_detail(subsidy_id)
            subsidy = result.get("result", [{}])[0] if result.get("result") else {}

            return jsonify({
                "success": True,
                "subsidy": {
                    "id": subsidy.get("id", ""),
                    "name": subsidy.get("name", ""),
                    "title": subsidy.get("title", ""),
                    "catch_phrase": subsidy.get("subsidy_catch_phrase", ""),
                    "detail": subsidy.get("detail", ""),
                    "use_purpose": subsidy.get("use_purpose", ""),
                    "industry": subsidy.get("industry", ""),
                    "target_employees": subsidy.get("target_number_of_employees", ""),
                    "subsidy_rate": subsidy.get("subsidy_rate", ""),
                    "subsidy_max_limit": format_subsidy_amount(subsidy.get("subsidy_max_limit")),
                    "detail_url": subsidy.get("front_subsidy_detail_page_url", ""),
                    "workflow": subsidy.get("workflow", []),
                    "source": "Jグランツ"
                }
            })

        except ValueError as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 400
        except ApiClientError as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    return app


def main():
    """
    アプリケーションのエントリーポイント
    """
    app = create_app()
    print(f"補助金検索アプリを起動します: http://{FLASK_HOST}:{FLASK_PORT}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
