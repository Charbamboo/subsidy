"""
補助金ポータル（福井県）スクレイピングモジュール

https://hojyokin-portal.jp/subsidies/list?pref_id=18 の全ページから
補助金情報を取得してJSON形式で保存します。
"""

import json
import time
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup


class SubsidyScraper:
    """補助金ポータルスクレイパー"""
    
    BASE_URL = "https://hojyokin-portal.jp/subsidies/list"
    DETAIL_BASE_URL = "https://hojyokin-portal.jp"
    DEFAULT_PREF_ID = 18  # 福井県
    ITEMS_PER_PAGE = 10  # 1ページあたりの件数
    
    def __init__(self, pref_id: int = DEFAULT_PREF_ID, delay: float = 1.0, fetch_details: bool = True):
        """
        Args:
            pref_id: 都道府県ID（デフォルト: 18 = 福井県）
            delay: リクエスト間の待機時間（秒）
            fetch_details: 詳細ページから追加情報を取得するかどうか
        """
        self.pref_id = pref_id
        self.delay = delay
        self.fetch_details = fetch_details
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
        })
        # 取得済みのURLを記録（重複防止）
        self.scraped_urls = set()
    
    def _build_url(self, page: int = 1) -> str:
        """ページURLを構築"""
        url = f"{self.BASE_URL}?pref_id={self.pref_id}"
        if page > 1:
            url += f"&page={page}"
        return url
    
    def _fetch_page(self, url: str) -> Optional[str]:
        """ページHTMLを取得"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"ページの取得に失敗しました ({url}): {e}")
            return None
    
    def _extract_subsidy_id(self, url: str) -> Optional[str]:
        """URLから補助金IDを抽出"""
        match = re.search(r'/subsidies/(\d+)', url)
        return match.group(1) if match else None
    
    def _parse_subsidy_card(self, card) -> Optional[dict]:
        """補助金カードから情報を抽出"""
        subsidy = {}
        
        # リンク要素を探してURLとIDを取得
        link = card.find("a", href=re.compile(r'/subsidies/\d+'))
        if not link:
            return None
        
        href = link.get("href", "")
        if not href.startswith("http"):
            href = self.DETAIL_BASE_URL + href
        
        # 重複チェック
        subsidy_id = self._extract_subsidy_id(href)
        if not subsidy_id or href in self.scraped_urls:
            return None
        
        self.scraped_urls.add(href)
        subsidy["id"] = subsidy_id
        subsidy["url"] = href
        
        # カード内のテキストを解析
        card_text = card.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in card_text.split("\n") if line.strip()]
        
        # ステータス（公募中、公募終了など）
        for line in lines:
            if line in ["公募中", "公募終了", "公募 中", "公募 終了"]:
                subsidy["status"] = line.replace(" ", "")
                break
        
        # タイトルを探す（都道府県名：「〜」のパターン）
        for line in lines:
            # 「」を含むタイトル行
            if "：「" in line or "「" in line:
                # ステータスを除去
                title = line.replace("公募中", "").replace("公募終了", "").strip()
                subsidy["title"] = title
                break
        
        # 都道府県
        for line in lines:
            if line in ["福井県", "北海道", "東京都", "大阪府", "愛知県", "福岡県", "新潟県", "石川県", "富山県"]:
                subsidy["prefecture"] = line
                break
        
        # 申請期間
        period_pattern = r'申請期間\s*(\d{4}年\d{1,2}月\d{1,2}日)?\s*[〜～]\s*(\d{4}年\d{1,2}月\d{1,2}日)?'
        for line in lines:
            if "申請期間" in line:
                subsidy["application_period"] = line.replace("申請期間", "").strip()
                match = re.search(period_pattern, line)
                if match:
                    if match.group(1):
                        subsidy["start_date"] = match.group(1)
                    if match.group(2):
                        subsidy["end_date"] = match.group(2)
                break
        
        # 上限金額
        for line in lines:
            if "上限金額" in line:
                amount = line.replace("上限金額", "").strip()
                subsidy["max_amount"] = amount
                break
        
        # 説明文（#で始まらない、特定のキーワードを含まない行を探す）
        exclude_keywords = ["公募中", "公募終了", "申請期間", "上限金額", "福井県", "北海道"]
        for line in lines:
            if (not line.startswith("#") and 
                "：「" not in line and 
                not any(kw in line for kw in exclude_keywords) and
                len(line) > 20):  # 説明文は20文字以上
                subsidy["description"] = line
                break
        
        # タグ
        tags = []
        for line in lines:
            if line.startswith("#"):
                # 複数のタグがつながっている場合は分割
                tag_parts = re.findall(r'#[^#]+', line)
                tags.extend([t.strip() for t in tag_parts])
        if tags:
            subsidy["tags"] = tags
        
        return subsidy
    
    def _parse_list_page(self, html: str) -> list:
        """一覧ページHTMLから補助金情報を抽出"""
        soup = BeautifulSoup(html, "html.parser")
        subsidies = []
        
        # 補助金カードを探す - aタグでsubsidies/数字を含むものの親要素を探す
        links = soup.find_all("a", href=re.compile(r'/subsidies/\d+'))
        
        # 各リンクの親要素（カード）を取得
        processed_cards = set()
        for link in links:
            # 親要素を辿ってカードを見つける
            card = link
            for _ in range(5):  # 最大5階層上まで探す
                parent = card.parent
                if parent is None:
                    break
                card = parent
                # カードらしい要素を見つけたら停止
                if card.name in ["article", "div", "li", "section"]:
                    card_html = str(card)
                    if card_html not in processed_cards and len(card.get_text()) > 50:
                        processed_cards.add(card_html)
                        subsidy = self._parse_subsidy_card(card)
                        if subsidy and subsidy.get("title"):
                            subsidies.append(subsidy)
                        break
        
        return subsidies
    
    def _get_total_count(self, html: str) -> int:
        """総件数を取得"""
        soup = BeautifulSoup(html, "html.parser")
        
        # "該当する補助金・助成金 831件" のようなテキストを探す
        text = soup.get_text()
        match = re.search(r'該当する補助金.*?(\d{1,4})\s*件', text)
        if match:
            return int(match.group(1))
        
        # 別のパターン
        match = re.search(r'(\d{1,4})\s*件', text)
        if match:
            return int(match.group(1))
        
        return 0
    
    def _get_total_pages(self, html: str) -> int:
        """総ページ数を取得"""
        # 総件数から計算
        total_count = self._get_total_count(html)
        if total_count > 0:
            return (total_count + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE
        
        # ページネーションリンクから取得
        soup = BeautifulSoup(html, "html.parser")
        max_page = 1
        
        # ページリンクを探す
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            match = re.search(r'page=(\d+)', href)
            if match:
                page_num = int(match.group(1))
                max_page = max(max_page, page_num)
        
        return max_page
    
    def _fetch_detail_page(self, url: str) -> dict:
        """詳細ページから追加情報を取得"""
        details = {}
        
        html = self._fetch_page(url)
        if not html:
            return details
        
        soup = BeautifulSoup(html, "html.parser")
        
        # 詳細情報を抽出
        # 概要・目的
        for header in soup.find_all(["h2", "h3", "h4", "dt", "th"]):
            header_text = header.get_text(strip=True)
            
            # 次の要素（値）を取得
            value_elem = header.find_next_sibling()
            if value_elem:
                value = value_elem.get_text(strip=True)
            else:
                value = ""
            
            if "概要" in header_text or "目的" in header_text:
                details["overview"] = value
            elif "対象者" in header_text or "対象" in header_text:
                details["target"] = value
            elif "補助率" in header_text:
                details["subsidy_rate"] = value
            elif "補助上限" in header_text or "補助金額" in header_text:
                details["subsidy_limit"] = value
            elif "対象経費" in header_text or "補助対象" in header_text:
                details["eligible_expenses"] = value
            elif "申請方法" in header_text:
                details["application_method"] = value
            elif "問い合わせ" in header_text or "連絡先" in header_text:
                details["contact"] = value
        
        # ページ全体から詳細テキストを取得（メインコンテンツ）
        main_content = soup.find("main") or soup.find("article") or soup.find(class_=re.compile(r'content|detail|main'))
        if main_content:
            # 長い説明文を抽出
            paragraphs = main_content.find_all("p")
            long_texts = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 50:
                    long_texts.append(text)
            if long_texts and "full_description" not in details:
                details["full_description"] = "\n".join(long_texts[:3])  # 最初の3段落
        
        # 公式サイトURL
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            text = link.get_text(strip=True)
            if "公式" in text or "詳細" in text or "申請" in text:
                if href.startswith("http") and "hojyokin-portal" not in href:
                    details["official_url"] = href
                    break
        
        return details
    
    def scrape_all(self, max_pages: Optional[int] = None) -> list:
        """全ページから補助金情報を取得
        
        Args:
            max_pages: 取得する最大ページ数（Noneの場合は全ページ）
            
        Returns:
            補助金情報のリスト
        """
        all_subsidies = []
        self.scraped_urls.clear()  # 重複チェック用セットをクリア
        
        # 最初のページを取得して総ページ数を確認
        print("ページ 1 を取得中...")
        first_page_url = self._build_url(1)
        html = self._fetch_page(first_page_url)
        if not html:
            return all_subsidies
        
        total_count = self._get_total_count(html)
        total_pages = self._get_total_pages(html)
        
        print(f"総件数: {total_count} 件")
        print(f"総ページ数: {total_pages}")
        
        if max_pages:
            total_pages = min(total_pages, max_pages)
            print(f"取得ページ数を {total_pages} に制限")
        
        print("-" * 50)
        
        # 全ページを取得
        for page in range(1, total_pages + 1):
            if page > 1:
                time.sleep(self.delay)  # サーバーに負荷をかけないよう待機
                print(f"ページ {page}/{total_pages} を取得中...")
                page_url = self._build_url(page)
                html = self._fetch_page(page_url)
                if not html:
                    continue
            
            subsidies = self._parse_list_page(html)
            all_subsidies.extend(subsidies)
            print(f"  -> {len(subsidies)} 件の補助金情報を取得（累計: {len(all_subsidies)} 件）")
        
        # 詳細ページから追加情報を取得
        if self.fetch_details and all_subsidies:
            print("-" * 50)
            print("詳細ページから追加情報を取得中...")
            for i, subsidy in enumerate(all_subsidies):
                if "url" in subsidy:
                    time.sleep(self.delay)
                    print(f"  詳細取得 {i+1}/{len(all_subsidies)}: {subsidy.get('title', '')[:30]}...")
                    details = self._fetch_detail_page(subsidy["url"])
                    if details:
                        subsidy["details"] = details
        
        return all_subsidies
    
    def save_to_json(self, subsidies: list, output_path: str = None) -> str:
        """補助金情報をJSONファイルに保存
        
        Args:
            subsidies: 補助金情報のリスト
            output_path: 出力ファイルパス（Noneの場合はdata/subsidies_fukui.json）
            
        Returns:
            保存したファイルのパス
        """
        if output_path is None:
            # src/data フォルダに保存
            output_dir = Path(__file__).parent.parent / "data"
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / "subsidies_fukui.json"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "metadata": {
                "source": self.BASE_URL,
                "prefecture_id": self.pref_id,
                "scraped_at": datetime.now().isoformat(),
                "total_count": len(subsidies)
            },
            "subsidies": subsidies
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return str(output_path)


def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="補助金ポータルから補助金情報をスクレイピング")
    parser.add_argument("--pref-id", type=int, default=18, help="都道府県ID（デフォルト: 18=福井県）")
    parser.add_argument("--max-pages", type=int, default=None, help="最大取得ページ数")
    parser.add_argument("--delay", type=float, default=1.5, help="リクエスト間の待機時間（秒）")
    parser.add_argument("--output", type=str, default=None, help="出力ファイルパス")
    parser.add_argument("--no-details", action="store_true", help="詳細ページの取得をスキップ")
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("補助金ポータル スクレイピング")
    print("=" * 50)
    print(f"都道府県ID: {args.pref_id}")
    print(f"詳細取得: {'無効' if args.no_details else '有効'}")
    print("-" * 50)
    
    scraper = SubsidyScraper(
        pref_id=args.pref_id, 
        delay=args.delay,
        fetch_details=not args.no_details
    )
    subsidies = scraper.scrape_all(max_pages=args.max_pages)
    
    if subsidies:
        output_path = scraper.save_to_json(subsidies, args.output)
        print("=" * 50)
        print(f"スクレイピング完了!")
        print(f"取得した補助金数: {len(subsidies)}")
        print(f"保存先: {output_path}")
    else:
        print("補助金情報を取得できませんでした。")


if __name__ == "__main__":
    main()
