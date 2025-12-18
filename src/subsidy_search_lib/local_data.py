"""
ローカルJSONファイルからの補助金データ検索
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any


class LocalSubsidySearcher:
    """
    ローカルJSONファイルから補助金を検索するクラス
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Args:
            data_dir: データディレクトリのパス（Noneの場合はデフォルト）
        """
        if data_dir is None:
            # src/data フォルダ
            self.data_dir = Path(__file__).parent.parent / "data"
        else:
            self.data_dir = Path(data_dir)
        
        self.subsidies: List[Dict] = []
        self.subsidies_by_id: Dict[str, Dict] = {}
        self._load_all_data()
    
    def _load_all_data(self):
        """データディレクトリ内のすべてのJSONファイルを読み込む"""
        self.subsidies = []
        self.subsidies_by_id = {}
        
        if not self.data_dir.exists():
            print(f"データディレクトリが見つかりません: {self.data_dir}")
            return
        
        for json_file in self.data_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # subsidies配列を取得
                if isinstance(data, dict) and "subsidies" in data:
                    subsidies = data["subsidies"]
                elif isinstance(data, list):
                    subsidies = data
                else:
                    continue
                
                for subsidy in subsidies:
                    if not isinstance(subsidy, dict):
                        continue
                    
                    # データソースを記録
                    subsidy["_source"] = "local"
                    subsidy["_source_file"] = json_file.name
                    
                    # IDがあれば辞書に追加
                    subsidy_id = subsidy.get("id")
                    if subsidy_id:
                        # ローカルデータのIDには "local_" プレフィックスを追加
                        local_id = f"local_{subsidy_id}"
                        subsidy["_local_id"] = local_id
                        self.subsidies_by_id[local_id] = subsidy
                    
                    self.subsidies.append(subsidy)
                
                print(f"ローカルデータ読み込み: {json_file.name} ({len(subsidies)}件)")
            
            except Exception as e:
                print(f"JSONファイル読み込みエラー ({json_file}): {e}")
    
    def reload_data(self):
        """データを再読み込み"""
        self._load_all_data()
    
    def search(
        self,
        keyword: str,
        target_area: Optional[str] = None,
        acceptance_only: bool = True
    ) -> List[Dict]:
        """
        キーワードで補助金を検索
        
        Args:
            keyword: 検索キーワード
            target_area: 対象地域（Noneの場合はすべて）
            acceptance_only: 公募中のみ検索するかどうか
            
        Returns:
            マッチした補助金のリスト
        """
        results = []
        keyword_lower = keyword.lower()
        
        for subsidy in self.subsidies:
            # キーワードマッチ
            searchable_text = self._get_searchable_text(subsidy).lower()
            if keyword_lower not in searchable_text:
                continue
            
            # 地域フィルタ
            if target_area:
                prefecture = subsidy.get("prefecture", "")
                if target_area not in prefecture and prefecture not in target_area:
                    # タグにも地域が含まれている場合がある
                    tags = subsidy.get("tags", [])
                    if not any(target_area in tag for tag in tags):
                        continue
            
            # 公募中フィルタ
            if acceptance_only:
                status = subsidy.get("status", "")
                if "公募中" not in status:
                    continue
            
            results.append(subsidy)
        
        return results
    
    def _get_searchable_text(self, subsidy: Dict) -> str:
        """検索対象のテキストを取得"""
        parts = [
            subsidy.get("title", ""),
            subsidy.get("description", ""),
            subsidy.get("prefecture", ""),
            subsidy.get("status", ""),
            subsidy.get("max_amount", ""),
        ]
        
        # タグ
        tags = subsidy.get("tags", [])
        if tags:
            parts.extend(tags)
        
        # 詳細情報
        details = subsidy.get("details", {})
        if details:
            parts.append(details.get("overview", ""))
            parts.append(details.get("full_description", ""))
            parts.append(details.get("target", ""))
            parts.append(details.get("eligible_expenses", ""))
        
        return " ".join(str(p) for p in parts if p)
    
    def get_by_id(self, local_id: str) -> Optional[Dict]:
        """
        IDで補助金を取得
        
        Args:
            local_id: ローカルID（"local_"プレフィックス付き）
            
        Returns:
            補助金データ（見つからない場合はNone）
        """
        return self.subsidies_by_id.get(local_id)
    
    def format_for_display(self, subsidy: Dict) -> Dict:
        """
        表示用にフォーマット
        
        Args:
            subsidy: 補助金データ
            
        Returns:
            表示用にフォーマットされた辞書
        """
        details = subsidy.get("details", {})
        
        return {
            "id": subsidy.get("_local_id", ""),
            "name": subsidy.get("title", "")[:30] + "..." if len(subsidy.get("title", "")) > 30 else subsidy.get("title", ""),
            "title": subsidy.get("title", ""),
            "target_area": subsidy.get("prefecture", ""),
            "subsidy_max_limit": subsidy.get("max_amount", "") or details.get("subsidy_limit", "") or "-",
            "subsidy_max_limit_raw": None,
            "acceptance_start": subsidy.get("start_date", ""),
            "acceptance_end": subsidy.get("end_date", ""),
            "target_employees": "-",
            "description": subsidy.get("description", ""),
            "status": subsidy.get("status", ""),
            "source": "補助金ポータル",
            "source_url": subsidy.get("url", ""),
            "tags": subsidy.get("tags", [])
        }
    
    def format_detail_for_display(self, subsidy: Dict) -> Dict:
        """
        詳細表示用にフォーマット
        
        Args:
            subsidy: 補助金データ
            
        Returns:
            詳細表示用にフォーマットされた辞書
        """
        details = subsidy.get("details", {})
        
        return {
            "id": subsidy.get("_local_id", ""),
            "name": subsidy.get("title", ""),
            "title": subsidy.get("title", ""),
            "catch_phrase": "",
            "detail": details.get("full_description", "") or subsidy.get("description", ""),
            "use_purpose": details.get("overview", ""),
            "industry": "-",
            "target_employees": details.get("target", "") or "-",
            "subsidy_rate": details.get("subsidy_rate", "") or "-",
            "subsidy_max_limit": subsidy.get("max_amount", "") or details.get("subsidy_limit", "") or "-",
            "detail_url": subsidy.get("url", ""),
            "workflow": [],
            "source": "補助金ポータル",
            "tags": subsidy.get("tags", []),
            "status": subsidy.get("status", ""),
            "application_period": subsidy.get("application_period", ""),
            "official_url": details.get("official_url", ""),
            "contact": details.get("contact", ""),
            "application_method": details.get("application_method", "")
        }

