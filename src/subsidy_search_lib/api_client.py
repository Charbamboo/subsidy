"""
Jグランツ API クライアント
APIとの通信処理を担当
"""

import json
import requests
from typing import Dict, List, Optional, Any
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
        keyword: Optional[str] = None,
        target_area: Optional[str] = None,
        subsidy_max_limit: Optional[int] = None,
        target_number_of_employees: Optional[str] = None,
        use_purpose: Optional[str] = None,
        acceptance_status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        条件を指定して補助金一覧を検索

        Args:
            keyword: キーワード検索（補助金名、詳細など）
            target_area: 対象地域
            subsidy_max_limit: 補助金上限額
            target_number_of_employees: 対象従業員数
            use_purpose: 利用目的
            acceptance_status: 受付状況（accepting: 受付中）

        Returns:
            Dict[str, Any]: API レスポンス（metadata と result を含む）

        Raises:
            requests.RequestException: API通信エラー
        """
        url = f"{self.base_url}{JGRANTS_SUBSIDIES_ENDPOINT}"

        # クエリパラメータの構築
        params = {}

        if keyword:
            params["keyword"] = keyword
        if target_area:
            params["target_area_search"] = target_area
        if subsidy_max_limit is not None:
            params["subsidy_max_limit"] = subsidy_max_limit
        if target_number_of_employees:
            params["target_number_of_employees"] = target_number_of_employees
        if use_purpose:
            params["use_purpose"] = use_purpose
        if acceptance_status:
            params["acceptance_status"] = acceptance_status

        try:
            # requestパラメータをJSON文字列として渡す
            query_params = {"request": json.dumps(params)} if params else None
            response = requests.get(
                url,
                params=query_params,
                timeout=self.timeout,
                headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            return response.json()
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
            requests.RequestException: API通信エラー
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

