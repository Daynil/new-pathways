# Just for using e.g. list[Item]
from __future__ import annotations

from dataclasses import dataclass
from json import loads
from os import listdir, makedirs
from pathlib import Path
from shutil import copy
from urllib import request
from typing import Union

from utilities import cprint, bcolors

wp_api_base_path = "http://admin.innerpathllc.com/wp-json/wp/v2"
project_base_path = Path(__file__).parent.parent


@dataclass
class NavItem:
    wp_id: int
    name: str
    parent_wp_id: int
    sort_order: int
    target_slug: str
    children: list[NavItem]


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


class DropdownChild:
    name: Union[str, None]
    href: str

    def __init__(self, name: Union[str, None], href: str):
        self.name = name
        self.href = href


def menu_item_solo(name: str, href: str) -> str:
    template = f"""
        <li class="nav-item">
          <a class="nav-link" aria-current="page" href="{href}">
            {name}
          </a>
        </li>
    """
    return template.strip()


def menu_dropdown_child(child: DropdownChild) -> str:
    if not child.name:
        return '<li><hr class="dropdown-divider"></li>'
    else:
        return f"""
            <li>
                <a class="dropdown-item" href="{child.href}">
                    {child.name}
                </a>
            </li>
        """.strip()


def menu_dropdown(name: str, children: list[DropdownChild]) -> str:
    children_tag = "{{children}}"
    parent_template = f"""
        <li class="nav-item dropdown">
          <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
            {name}
          </a>
          <ul class="dropdown-menu">
            {children_tag}
          </ul>
        </li>
    """

    children_template = ""
    for child in children:
        children_template += menu_dropdown_child(child)

    return parent_template.replace(children_tag, children_template)


def get_menu() -> str:
    menu = wp_get_all("menu")
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

    # Collect base menu and child items when present for parent menus
    anchors = []
    parent_items: list[NavItem] = [item for item in nav_arr if item.parent_wp_id == 0]
    for parent in nav_arr:
        parent.children = [
            child for child in nav_arr if child.parent_wp_id == parent.wp_id
        ]
        if len(parent.children) > 0:
            anchors.append({"id": parent.wp_id, "el": None})

    main_menu = ""
    parent_items.sort(key=lambda item: item.sort_order)

    # Generate the HTML string for all the nav links
    for parent in parent_items:
        if len(parent.children) > 0:
            parent.children.sort(key=lambda item: item.sort_order)
            children = [
                DropdownChild(name=child.name, href=f"/{child.target_slug}.html")
                for child in parent.children
            ]
            main_menu += menu_dropdown(parent.name, children)
        else:
            if parent.name == "Home":
                main_menu += menu_item_solo(parent.name, "/")
            else:
                main_menu += menu_item_solo(parent.name, f"/{parent.target_slug}.html")

    with project_base_path.joinpath("src/navbar.html").open("r") as f:
        main_menu = f.read().replace("{{main_menu}}", main_menu)

    return main_menu


def build(clean=False):
    src = project_base_path / "src"
    build_base_path = project_base_path / "public"

    if clean and build_base_path.exists():
        build_base_path.unlink()

    makedirs(build_base_path, exist_ok=True)

    # Copy all static files to the public dir as is
    for static_filename in listdir(src / "static"):
        copy(src / "static" / static_filename, build_base_path)

    with src.joinpath("layout.html").open("r") as f:
        layout = f.read()

    pages = wp_get_all("pages")

    # For each standard Wordpress page, generate an HTML page using our layout template
    for page in pages:
        is_index = page["title"]["rendered"] == "Home"

        if not page["status"] == "publish":
            continue

        page_built = (
            layout.replace(r"{{nav}}", get_menu())
            .replace(r"{{title}}", page["title"]["rendered"] if not is_index else "")
            .replace(r"{{contents}}", page["content"]["rendered"])
        )
        with build_base_path.joinpath(
            "index.html" if is_index else f"{page['slug']}.html",
        ).open("w", encoding="utf-8") as f:
            f.write(page_built)


if __name__ == "__main__":
    cprint("Rebuilding...", bcolors.WARNING)
    build()
    cprint("Complete!", bcolors.OKGREEN)
