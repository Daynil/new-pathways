# Just for using e.g. list[Item]
from __future__ import annotations

from dataclasses import dataclass
from json import loads
from os import listdir, makedirs
from pathlib import Path
from shutil import copy
from urllib import request

wp_api_base_path = "http://admin.innerpathllc.com/wp-json/wp/v2"


@dataclass
class NavItem:
    wp_id: int
    name: str
    parent_wp_id: int
    sort_order: int
    target_slug: str
    children: list[NavItem]


# @dataclass
# class ParentNavItem(NavItem):
#     children: list[NavItem]


def wp_get_all(url: str):
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

    return wp_res


def build():
    build_base_path = Path(__file__).parent.parent.joinpath("public")
    src = Path(__file__).parent

    menu = wp_get_all("menu")
    nav_arr: list[NavItem] = []
    for menu_item in menu:
        item_url_parts = menu_item["url"].split("/")
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

        target_slug = (
            item_url_parts[-2] if item_url_parts[-1] == "" else item_url_parts[-1]
        )
        if menu_item["title"] == "Home":
            target_slug = "/"
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

    pages = wp_get_all("pages")

    anchors = []
    parent_items: list[NavItem] = [item for item in nav_arr if item.parent_wp_id == 0]
    for parent in nav_arr:
        parent.children = [
            child for child in nav_arr if child.parent_wp_id == parent.wp_id
        ]
        if len(parent.children) > 0:
            anchors.append({"id": parent.wp_id, "el": None})

    main_menu = '<ul class="base-nav"><span class="logo"><img src="logo.png" /></span><span class="push"></span>'
    parent_items.sort(key=lambda item: item.sort_order)

    for parent in parent_items:
        if len(parent.children) > 0:
            submenu = '<ul class="dropdown-content">'
            # anchor =
            parent.children.sort(key=lambda item: item.sort_order)
            for child in parent.children:
                submenu += (
                    f'<li><a href="/{child.target_slug}.html">{child.name}</a></li>'
                )
            submenu += "</ul>"
            main_menu += (
                f'<li class="dropdown base-nav-item"><a href="#">{parent.name}</a>'
                + submenu
                + "</li>"
            )
        else:
            if parent.name == "Home":
                main_menu += (
                    f'<li class="base-nav-item"><a href="/">{parent.name}</a></li>'
                )
            else:
                main_menu += f'<li class="base-nav-item"><a href="/{parent.target_slug}.html">{parent.name}</a></li>'

    main_menu += '</ul><span class="nav-end"></span>'

    makedirs(build_base_path, exist_ok=True)

    for static_filename in listdir(src / "static"):
        copy(src / "static" / static_filename, build_base_path)

    with src.joinpath("layout.html").open("r") as f:
        layout = f.read()

    for page in pages:
        is_index = page["title"]["rendered"] == "Home"

        if not page["status"] == "publish":
            continue

        page_built = (
            layout.replace(r"{{nav}}", main_menu)
            .replace(r"{{title}}", page["title"]["rendered"] if not is_index else "")
            .replace(r"{{contents}}", page["content"]["rendered"])
        )
        with build_base_path.joinpath(
            "index.html" if is_index else f"{page['slug']}.html",
        ).open("w", encoding="utf-8") as f:
            f.write(page_built)


if __name__ == "__main__":
    print("Rebuilding...")
    build()
    print("Complete!")
