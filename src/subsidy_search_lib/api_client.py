"""
Jグランツ API クライアント
APIとの通信処理を担当
"""

import json
import requests
from typing import Dict, Optional, Any
from .config import (
    JGRANTS_API_BASE_URL,
    JGRANTS_SUBSIDIES_ENDPOINT,
    JGRANTS_SUBSIDY_DETAIL_ENDPOINT,
    API_TIMEOUT
)


class JGrantsApiClient:
    """
    Jグランツ APIクライアントクラス
    補助金一覧取得と詳細取得のAPIを呼び出す
    """

    def __init__(self):
        """クライアントの初期化"""
        self.base_url = JGRANTS_API_BASE_URL
        self.timeout = API_TIMEOUT

    def search_subsidies(
        self,
        keyword: str,
        sort: str = "created_date",
        order: str = "DESC",
        acceptance: str = "1",
        target_area: Optional[str] = None,
        target_number_of_employees: Optional[str] = None,
        use_purpose: Optional[str] = None,
        industry: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        条件を指定して補助金一覧を検索

        Args:
            keyword: 検索キーワード（必須、2文字以上）
            sort: ソート項目（必須）
                - created_date: 作成日時
                - acceptance_start_datetime: 募集開始日時
                - acceptance_end_datetime: 募集終了日時
            order: ソート順（必須）
                - ASC: 昇順
                - DESC: 降順
            acceptance: 募集期間内絞込（必須）
                - "0": 否
                - "1": 要
            target_area: 対象地域
            target_number_of_employees: 対象従業員数
            use_purpose: 利用目的
            industry: 業種

        Returns:
            Dict[str, Any]: API レスポンス（metadata と result を含む）

        Raises:
            ApiClientError: API通信エラー
        """
        url = f"{self.base_url}{JGRANTS_SUBSIDIES_ENDPOINT}"

        # 必須パラメータの構築
        params = {
            "keyword": keyword,
            "sort": sort,
            "order": order,
            "acceptance": acceptance
        }

        # オプションパラメータの追加
        if target_area:
            params["target_area_search"] = target_area
        if target_number_of_employees:
            params["target_number_of_employees"] = target_number_of_employees
        if use_purpose:
            params["use_purpose"] = use_purpose
        if industry:
            params["industry"] = industry

        try:
            # パラメータを直接クエリパラメータとして渡す
            response = requests.get(
                url,
                params=params,
                timeout=self.timeout,
                headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            # HTTPエラーの詳細を取得
            error_detail = ""
            try:
                error_json = e.response.json()
                error_detail = error_json.get("message", str(error_json))
            except Exception:
                error_detail = e.response.text[:200] if e.response.text else ""
            raise ApiClientError(f"API通信エラー: {str(e)} - {error_detail}") from e
        except requests.RequestException as e:
            raise ApiClientError(f"API通信エラー: {str(e)}") from e

    def get_subsidy_detail(self, subsidy_id: str) -> Dict[str, Any]:
        """
        補助金の詳細情報を取得

        Args:
            subsidy_id: 補助金ID（18文字以下）

        Returns:
            Dict[str, Any]: 補助金詳細情報

        Raises:
            ApiClientError: API通信エラー
            ValueError: 補助金IDが不正な場合
        """
        if not subsidy_id or len(subsidy_id) > 18:
            raise ValueError("補助金IDは1〜18文字で指定してください")

        url = f"{self.base_url}{JGRANTS_SUBSIDY_DETAIL_ENDPOINT}/{subsidy_id}"

        try:
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise ApiClientError(f"API通信エラー: {str(e)}") from e


class ApiClientError(Exception):
    """APIクライアントエラー"""
    pass


def format_subsidy_amount(amount: Optional[int]) -> str:
    """
    補助金額を読みやすい形式にフォーマット

    Args:
        amount: 金額（円）

    Returns:
        str: フォーマットされた金額文字列
    """
    if amount is None:
        return "上限なし"

    if amount >= 100000000:  # 1億円以上
        return f"{amount / 100000000:.1f}億円"
    elif amount >= 10000:  # 1万円以上
        return f"{amount / 10000:.0f}万円"
    else:
        return f"{amount:,}円"

