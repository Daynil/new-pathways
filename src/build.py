# Just for using e.g. list[Item]
from __future__ import annotations

import json
from dataclasses import dataclass
from json import loads
from os import listdir, makedirs
from pathlib import Path
from shutil import copy
from urllib import request
from typing import Union

from jinja2 import Environment, FileSystemLoader

from utilities import cprint, CColors

wp_api_base_path = "http://admin.innerpathllc.com/wp-json/wp/v2"
project_base_path = Path(__file__).parent.parent

jenv = Environment(loader=FileSystemLoader(project_base_path/"src/templates"))

@dataclass
class NavItem:
    wp_id: int
    name: str
    parent_wp_id: int
    sort_order: int
    target_slug: str
    children: list[NavItem]


def wp_get_all(url: str, use_cache=False):
    cache = project_base_path / f"src/tmp/wp_{url}.json"

    if use_cache:
        if cache.exists():
            with cache.open("r") as f:
                return json.load(f)

    wp_res = []
    cur_res_length = 100
    cur_page = 1

    while cur_res_length == 100:
        wp_res_data = request.urlopen(
            f"{wp_api_base_path}/{url}?per_page=100&page={cur_page}"
        )
        wp_res_page = loads(wp_res_data.read())
        wp_res += wp_res_page
        cur_res_length = len(wp_res_page)
        cur_page += 1

    if use_cache:
        with cache.open("w+") as f:
            json.dump(wp_res, f)

    return wp_res


def get_menu(use_cache=False) -> str:
    menu = wp_get_all("menu", use_cache)
    nav_arr: list[NavItem] = []

    # Convert raw menu dictionary to typed Python class
    for menu_item in menu:
        item_url_parts = menu_item["url"].split("/")

        # Parent items that aren't a link themselves, but have
        # Sub-items (aka click/hover to expand submenu)
        if item_url_parts[0] == "":
            nav_arr.append(
                NavItem(
                    menu_item["ID"],
                    menu_item["title"],
                    0,
                    menu_item["menu_order"],
                    "",
                    [],
                )
            )
            continue

        # Base menu items or sub-items for a parent menu
        target_slug = (
            item_url_parts[-2] if item_url_parts[-1] == "" else item_url_parts[-1]
        ) + ".html"
        if menu_item["title"] == "Home":
            target_slug = ""
        nav_arr.append(
            NavItem(
                menu_item["ID"],
                menu_item["title"],
                int(menu_item["menu_item_parent"]),
                menu_item["menu_order"],
                target_slug,
                [],
            )
        )

    # Collect base menu and child items when present for parent menus
    parent_items = sorted(
        [item for item in nav_arr if item.parent_wp_id == 0],
        key=lambda item: item.sort_order,
    )
    for parent in parent_items:
        parent.children = sorted(
            [child for child in nav_arr if child.parent_wp_id == parent.wp_id],
            key=lambda item: item.sort_order,
        )

    return jenv.get_template('navbar.html').render(
        main_menu=parent_items
    )


def build(clean=False, use_wp_cache=False):
    src = project_base_path / "src"
    build_base_path = project_base_path / "public"

    if clean and build_base_path.exists():
        build_base_path.unlink()

    makedirs(build_base_path, exist_ok=True)

    # Copy cached static file to public dir only on clean build
    if clean:
        for static_filename in listdir(src / "static-cached"):
            copy(src / "static-cached" / static_filename, build_base_path)

    pages = wp_get_all("pages", use_wp_cache)
    nav = get_menu(use_wp_cache)
    pdfs = [
        {
            "slug": pdf["slug"],
            "display_string": pdf["title"]["rendered"],
            "url": pdf["source_url"],
        }
        for pdf in wp_get_all("media")
        if pdf["mime_type"] == "application/pdf"
    ]

    for pdf in pdfs:
        pdf_path = build_base_path.joinpath(f"{pdf['slug']}.pdf")
        # For dev purposes, avoid redownloading every rebuild
        if not pdf_path.exists():
            request.urlretrieve(pdf["url"], pdf_path)

    # Copy all static files to the public dir as is
    for static_filename in listdir(src / "static"):
        copy(src / "static" / static_filename, build_base_path)

    article_template = jenv.get_template("article.html")
    # For each standard Wordpress page, generate an HTML page using our layout template
    for page in pages:
        if not page["status"] == "publish":
            continue

        is_index = page["title"]["rendered"] == "Home"
        title = page["title"]["rendered"] if page["title"]["rendered"] != "Home" else ""

        template_name = title.lower().replace(" ", "-")
        if not src.joinpath(f"templates/{template_name}.html").exists():
            # Pages with article template
            rendered_page = article_template.render(
                nav=nav,
                title=title,
                wordpress_source=page["content"]["rendered"],
            )
        else:
            # Pages with their own template
            rendered_page = jenv.get_template(
                f"{template_name}.html"
            ).render(nav=nav, title=title, wordpress_source=page["content"]["rendered"], pdfs=pdfs)

        with build_base_path.joinpath(
                "index.html" if is_index else f"{page['slug']}.html",
        ).open("w", encoding="utf-8") as f:
            f.write(rendered_page)


if __name__ == "__main__":
    cprint("Rebuilding...", CColors.WARNING)
    build(use_wp_cache=True)
    cprint("Complete!", CColors.OKGREEN)
