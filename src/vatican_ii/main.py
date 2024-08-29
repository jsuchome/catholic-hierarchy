import csv
import re
import tempfile
from typing import Optional

import requests
from bs4 import BeautifulSoup

OUTPUT_FILE = "vatican_ii.csv"


def parse_page(url: str, file_path: Optional[str] = None) -> None:
    """Parses the given URL or file path to extract the council fathers."""
    if file_path:
        with open(file_path, encoding="utf-8") as file:
            html_content = file.read()
    else:
        response = requests.get(url)

        if response.status_code == 200:
            html_content = response.text
        else:
            print(f"Failed to retrieve the page. Status code: {response.status_code}")
            return

    soup = BeautifulSoup(html_content, "html.parser")

    h3_tag = soup.find("h3", string=lambda text: text and "Council Fathers, Page" in text)

    if not h3_tag:
        print("Failed to find the h3 tag.")
        return

    ul_tag = h3_tag.find_next("ul")
    if not ul_tag:
        print("Failed to find the ul tag.")
        return

    for element in ul_tag.descendants:
        if element.name == "li":
            # it seems it can be parsed by taking all li elements into one...
            # so I need to treat them as strings for time being
            full_list = str(element)
            break
    elements = list(filter(None, full_list.split("<li>")))

    without_country = []
    titulars = []
    cardinals = []

    # Re-parse each element back into BeautifulSoup for further processing
    for _idx, string_item in enumerate(elements, start=1):
        item = BeautifulSoup("<li>" + string_item, "html.parser")

        for b_tag in item.find_all("b"):
            b_tag.unwrap()  # remove the <b> tags

        text = item.get_text().replace("†", "").strip()

        titular = False
        cardinal = False

        if "Titular" in text:
            titulars.append(text)
            titular = True
        if "Cardinal" in text:
            cardinals.append(text)
            cardinal = True

        # example of the item source:
        # <li><a href="/bishop/bberp.html">Jackson <b>Berenguer Prado</b></a> †, Bishop of <a href="/diocese/dfeir.html">Feira de Santana</a>, Bahia, <a href="/country/br.html">Brazil</a>; Age: 44.4
        # <li><a href="/bishop/balbareda.html">Joaquín Anselmo María Albareda y Ramoneda</a>, O.S.B. †, Cardinal, Priest of <a href="/diocese/dqosb.html">Order of Saint Benedict</a>; Age: 70.6
        # <li><a href="/bishop/bagni.html">Thomas Roch <b>Agniswami</b></a>, S.J. &#8224;, Bishop of <a href="/diocese/dkott.html">Kottar</a>
        # <li><a href="/bishop/bballes.html">Anastasio Alberto <b>Ballestrero</b></a>, O.C.D. &#8224;, Superior General of <a href="/diocese/dqocd.html">Order of Discalced Carmelites</a>

        a_tags = item.find_all("a")
        name = a_tags[0].get_text().strip()
        diocese = (
            a_tags[1].get_text().strip()
        )  # FIXME this may be congregation! Does the missing country imply 'diocese' is congregation?
        country = a_tags[2].get_text().strip() if len(a_tags) > 2 else None
        age = (
            re.search(r"Age: (\d+\.\d+)", text).group(1) if "Age" in text else None
        )  # FIXME find fathers without age (check their page?)

        # only search for order in the substring from start to the second 'a' tag:
        order = ""
        first_part = text[: text.find(a_tags[1].get_text())]
        if first_part and first_part.count(",") > 1:
            _order = re.search(r", ([^,]+),", first_part).group(1).strip()
            if "Cardinal" not in _order and "ishop" not in _order:
                order = _order

        if country is None and "Titular" not in text:
            without_country.append(text)

        with open(OUTPUT_FILE, "a", newline="") as file:
            writer = csv.writer(file)
            field = [name, age, order, diocese, country, cardinal, titular]
            writer.writerow(field)

    print(f"Total number of council fathers on this page: {len(elements)}")
    print(f"Total number of titular bishops: {len(titulars)}")
    print(f"Total number of council fathers without country (excluding titular): {len(without_country)}")


def save_page_to_tempfile(url: str) -> str:
    """Fetches the HTML content from the given URL and saves it to a temporary file.

    :param url: The URL of the page to fetch.
    :return: The path to the temporary file containing the HTML content.
    """
    response = requests.get(url)

    if response.status_code == 200:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8")
        temp_file.write(response.text)
        temp_file.close()
        return temp_file.name
    raise Exception(f"Failed to retrieve the page. Status code: {response.status_code}")


def main() -> None:
    """Main function to run the scrapper."""
    with open(OUTPUT_FILE, "w", newline="") as file:
        writer = csv.writer(file)
        field = ["Name", "Age", "Order", "Diocese", "Country", "Cardinal", "Titular"]
        writer.writerow(field)

    for page in range(1, 14):
        url = f"https://catholic-hierarchy.org/event/ecv2-1-{page}.html"
        print(f"Processing URL: {url}")
        parse_page(url)


if __name__ == "__main__":
    main()
