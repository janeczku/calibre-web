import concurrent.futures
import requests
from bs4 import BeautifulSoup as BS
from typing import List, Optional
import json

try:
    import cchardet
except ImportError:
    pass

from cps.services.Metadata import MetaRecord, MetaSourceInfo, Metadata
import cps.logger as logger

log = logger.create()


class Goodreads(Metadata):
    __name__ = "Goodreads"
    __id__ = "goodreads"
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    session = requests.Session()
    session.headers = headers

    def search(self, query: str, generic_cover: str = "", locale: str = "en") -> Optional[List[MetaRecord]]:
        def inner(link, index):
            try:
                r = self.session.get(link)
                r.raise_for_status()
            except Exception as ex:
                log.warning(ex)
                return []
            soup = BS(r.content, "lxml")
            try:
                match = MetaRecord(
                    title="",
                    authors="",
                    source=MetaSourceInfo(
                        id=self.__id__,
                        description="Goodreads",
                        link="https://www.goodreads.com/"
                    ),
                    url=link,
                    publisher="",
                    publishedDate="",
                    id=None,
                    tags=[]
                )
                try:
                    script = soup.find("script", type="application/ld+json")
                    data = json.loads(script.string) if script else {}

                    match.title = data.get("name", "")
                    match.cover = data.get("image", "")
                    
                    # This one preserves what each contributor did (i.e. editor, translator)
                    try:
                        authors = []
                        contributor_section = soup.select_one("div.BookPageMetadataSection__contributor")
                        if contributor_section:
                            for contributor in contributor_section.select("a.ContributorLink"):
                                name_tag = contributor.select_one("span.ContributorLink__name")
                                role_tag = contributor.select_one("span.ContributorLink__role")
                                name = name_tag.get_text(strip=True) if name_tag else ""
                                role = role_tag.get_text(strip=True).strip("()") if role_tag else ""
                                if role:
                                    authors.append(f"{name} ({role})")
                                else:
                                    authors.append(name)
                        match.authors = authors
                    except Exception:
                        match.authors = []

                    rating_val = data.get("aggregateRating", {}).get("ratingValue", 0)
                    match.rating = int(float(rating_val)) if rating_val else 0
                except Exception:
                    pass

                desc = soup.select_one("div.BookPageMetadataSection__description span.Formatted")
                match.description = "\n".join(desc.stripped_strings) if desc else ""

                return match, index
            except Exception as e:
                log.error_or_exception(e)
                return []

        if not self.active:
            return []

        try:
            res = self.session.get(f"https://www.goodreads.com/search?q={query.replace(' ', '+')}", headers=self.headers)
            res.raise_for_status()
        except Exception as e:
            log.warning(e)
            return []

        soup = BS(res.content, 'html.parser')
        links = ["https://www.goodreads.com" + a["href"] for a in soup.select("a.bookTitle[href]")[:3]]

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(inner, link, idx): idx for idx, link in enumerate(links)}
            results = []
            for fut in concurrent.futures.as_completed(futures):
                res = fut.result()
                if res:
                    results.append(res)

        return [x[0] for x in sorted(results, key=lambda x: x[1])]
