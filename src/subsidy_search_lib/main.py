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
            sort_orders=SORT_ORDERS
        )

    @app.route("/search", methods=["POST"])
    def search():
        """
        補助金を検索してJSON形式で結果を返す
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

            # キーワードのバリデーション（2文字以上必須）
            if not keyword or len(keyword) < 2:
                return jsonify({
                    "success": False,
                    "error": "検索キーワードは2文字以上で入力してください"
                }), 400

            # API呼び出し
            result = api_client.search_subsidies(
                keyword=keyword,
                sort=sort,
                order=order,
                acceptance=acceptance,
                target_area=target_area,
                target_number_of_employees=target_number_of_employees,
                use_purpose=use_purpose
            )

            # 結果のフォーマット
            subsidies = result.get("result", [])
            formatted_subsidies = []

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
                    "target_employees": subsidy.get("target_number_of_employees", "")
                })

            return jsonify({
                "success": True,
                "count": result.get("metadata", {}).get("resultset", {}).get("count", 0),
                "subsidies": formatted_subsidies
            })

        except ApiClientError as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
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
                    "workflow": subsidy.get("workflow", [])
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

