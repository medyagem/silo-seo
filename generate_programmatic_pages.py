#!/usr/bin/env python3
import argparse
import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from string import Template


@dataclass
class City:
    name: str
    population: str
    region: str
    districts: list[str]


def slugify(value: str) -> str:
    replacements = {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
        "Ç": "c",
        "Ğ": "g",
        "İ": "i",
        "I": "i",
        "Ö": "o",
        "Ş": "s",
        "Ü": "u",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    value = value.lower()
    cleaned = []
    for ch in value:
        if ch.isalnum():
            cleaned.append(ch)
        elif ch in {" ", "-", "_"}:
            cleaned.append("-")
    slug = "".join(cleaned)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def load_cities(path: str) -> list[City]:
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        cities = []
        for row in reader:
            districts = [d.strip() for d in row["districts"].split("|") if d.strip()]
            cities.append(
                City(
                    name=row["city"].strip(),
                    population=row["population"].strip(),
                    region=row["region"].strip(),
                    districts=districts,
                )
            )
        return cities


def load_template(path: str) -> Template:
    with open(path, encoding="utf-8") as handle:
        return Template(handle.read())


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def render_page(template: Template, context: dict[str, str]) -> str:
    return template.safe_substitute(context)


def build_service_links(base_url: str, sector_slug: str, city_slug: str, services: list[str]) -> str:
    items = []
    for service in services:
        service_slug = slugify(service)
        url = f"{base_url}/{sector_slug}/{service_slug}/{city_slug}/"
        items.append(f'<li><a href="{url}">{service} {city_slug}</a></li>')
    return "\n".join(items)


def main() -> None:
    parser = argparse.ArgumentParser(description="Programatik SEO sayfa üretici")
    parser.add_argument("--sector", help="Sektör anahtarı (sectors.json içinde)")
    parser.add_argument("--data", default="data/cities.csv", help="Şehir verisi CSV yolu")
    parser.add_argument("--sectors", default="data/sectors.json", help="Sektörler JSON dosyası")
    parser.add_argument("--template", default="templates/page.html", help="HTML şablon dosyası")
    parser.add_argument("--output", default="dist", help="Çıktı klasörü")
    parser.add_argument("--base-url", default="https://example.com", help="Sitemap için temel URL")
    args = parser.parse_args()

    with open(args.sectors, encoding="utf-8") as handle:
        sectors_data = json.load(handle)

    if args.sector:
        sector_key = args.sector
    else:
        sector_key = input(f"Sektör seçin {list(sectors_data.keys())}: ").strip()

    if sector_key not in sectors_data:
        raise SystemExit(f"Sektör bulunamadı: {sector_key}")

    sector = sectors_data[sector_key]
    sector_slug = slugify(sector["slug"])
    services = sector["services"]

    cities = load_cities(args.data)
    template = load_template(args.template)

    output_paths = []
    for city in cities:
        city_slug = slugify(city.name)
        district_items = "\n".join([f"<li>{d}</li>" for d in city.districts])
        service_links = build_service_links(args.base_url, sector_slug, city_slug, services)

        for service in services:
            service_slug = slugify(service)
            page_dir = os.path.join(args.output, sector_slug, service_slug, city_slug)
            ensure_dir(page_dir)

            context = {
                "city": city.name,
                "city_slug": city_slug,
                "region": city.region,
                "population": city.population,
                "service": service,
                "service_slug": service_slug,
                "sector": sector["name"],
                "district_list": district_items,
                "service_links": service_links,
                "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            }

            html = render_page(template, context)
            output_file = os.path.join(page_dir, "index.html")
            with open(output_file, "w", encoding="utf-8") as handle:
                handle.write(html)
            output_paths.append(f"{args.base_url}/{sector_slug}/{service_slug}/{city_slug}/")

    sitemap_path = os.path.join(args.output, "sitemap.xml")
    ensure_dir(args.output)
    with open(sitemap_path, "w", encoding="utf-8") as handle:
        handle.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        handle.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for url in output_paths:
            handle.write("  <url>\n")
            handle.write(f"    <loc>{url}</loc>\n")
            handle.write("    <changefreq>weekly</changefreq>\n")
            handle.write("  </url>\n")
        handle.write("</urlset>\n")

    print(f"Toplam {len(output_paths)} sayfa üretildi.")
    print(f"Sitemap oluşturuldu: {sitemap_path}")


if __name__ == "__main__":
    main()
