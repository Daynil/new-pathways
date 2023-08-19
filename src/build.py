# Just for using e.g. list[Item]
from __future__ import annotations

import platform
import subprocess
import sys
import traceback
from dataclasses import dataclass
from json import loads
from os import listdir, makedirs
from pathlib import Path
from shutil import copy
from typing import Optional
from urllib import request

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

    # main_menu = '<ul class="base-nav"><span class="logo"><img src="logo.png" /></span><span class="push"></span>'
    with project_base_path.joinpath("src/navbar.html").open("r") as f:
        main_menu = f.read()

    parent_items.sort(key=lambda item: item.sort_order)

    # Generate the HTML string for all the nav links
    parent_menu = ""
    for parent in parent_items:
        if False:
            pass
        # if len(parent.children) > 0:
        #     submenu = '<ul class="dropdown-content">'
        #     parent.children.sort(key=lambda item: item.sort_order)
        #     for child in parent.children:
        #         submenu += (
        #             f'<li><a href="/{child.target_slug}.html">{child.name}</a></li>'
        #         )
        #     submenu += "</ul>"
        #     parent_menu += (
        #         f'<li class="dropdown base-nav-item"><a href="#">{parent.name}</a>'
        #         + submenu
        #         + "</li>"
        #     )
        else:
            if parent.name == "Home":
                parent_menu += f'<a href="/" class="text-gray-300 hover:bg-gray-700 hover:text-white rounded-md px-3 py-2 text-sm font-medium">{parent.name}</a>'
                # parent_menu += (
                #     f'<li class="base-nav-item"><a href="/">{parent.name}</a></li>'
                # )
            else:
                parent_menu += f'<a href="{parent.target_slug}.html" class="text-gray-300 hover:bg-gray-700 hover:text-white rounded-md px-3 py-2 text-sm font-medium" aria-current="page">{parent.name}</a>'
                # parent_menu += f'<li class="base-nav-item"><a href="/{parent.target_slug}.html">{parent.name}</a></li>'

    # main_menu += '</ul><span class="nav-end"></span>'
    main_menu = main_menu.replace(r"{{main_menu}}", parent_menu)

    return main_menu


def check_tailwind():
    """
    Check if tailwindcss cli is downloaded, do so if not
    """
    tailwind_platform_version = "tailwindcss-windows-x64.exe"
    tailwind_local = project_base_path / "tailwindcss.exe"

    bits, _ = platform.architecture()

    if sys.platform != "win32":
        # TODO: find out if this is the correct architecture for netlify
        tailwind_platform_version = "tailwindcss-linux-x64"
        tailwind_local = tailwind_local.parent / "tailwindcss"

    if len(list(project_base_path.glob("tailwindcss*"))):
        return tailwind_local

    print("Downloading tailwindcss...")

    run_cmd(
        [
            f"curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/{tailwind_platform_version}",
            f"mv {tailwind_local.parent/tailwind_platform_version} {tailwind_local}",
        ],
        raise_on_stderr=True,
    )

    if sys.platform != "win32":
        run_cmd(f"chmod +x {tailwind_local}", raise_on_stderr=True)

    print("Tailwindcss downloaded")
    return tailwind_local


def build():
    tailwind_local = check_tailwind()

    src = project_base_path / "src"
    build_base_path = project_base_path / "public"

    main_menu = get_menu()

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
            layout.replace(r"{{nav}}", main_menu)
            .replace(r"{{title}}", page["title"]["rendered"] if not is_index else "")
            .replace(r"{{contents}}", page["content"]["rendered"])
        )
        with build_base_path.joinpath(
            "index.html" if is_index else f"{page['slug']}.html",
        ).open("w", encoding="utf-8") as f:
            f.write(page_built)

    run_cmd(
        f"{tailwind_local} -i {src/'input.css'} -o {build_base_path/'output.css'} --content '{build_base_path}\**\*.{{html,js,css}}'",
        raise_on_exit_code=True,
        print_output=False,
    )


def run_cmd(
    commands: str | list[str],
    print_output=True,
    format_output=False,
    escape_str=False,
    show_args_used=False,
    raise_on_stderr=False,
    raise_on_exit_code=False,
    input: Optional[str] = None,
    ssh_host="",
):
    """
    Execute commands with powershell.
    If multiple commands provided, they are issued one at a time, and their
    proccess output is combined and returned as 1 CompletedProcess.
    Waits for the completion of the commands before returning.

    Args:
        commands: A command, or list of commands.
        print_output: Prints stdout to terminal, for common use case without
        having to manually grab process.stdout and print it.
        format_output: Whether to format printed output with rich.
        escape_str: Printed string escaping.
        show_args_used: Shows full argument list issued, for debugging.
        raise_on_stderr: Raises on stderr, for common use case without having
        to manually grab process.stderr and raise it or end the program.
        input: `subprocess.run` passthrough.
        ssh_host: `user@host` for where to issue commands. If not provided,
        commands issued locally.

    Returns:
        Output for all commands combined into a single subprocess.CompletedProcess
    """
    if isinstance(commands, str):
        commands = [commands]

    combined_process = subprocess.CompletedProcess([], 0, "", "")

    for idx, command in enumerate(commands):
        powershell_path = r"C:\Program Files\PowerShell\7\pwsh.exe"
        subprocess_args = [
            powershell_path,
            "-Command",
        ]
        if ssh_host:
            subprocess_args.append("ssh " + ssh_host)
        subprocess_args.append(command)
        process = subprocess.run(
            subprocess_args,
            text=True,
            capture_output=True,
            input=input,
        )

        process_idx = f"[{idx}] " if len(commands) > 1 else ""
        combined_process.args += process.args
        combined_process.returncode += process.returncode
        combined_process.stdout += (
            process_idx + "\n" if idx > 0 else "" + process.stdout
        )
        combined_process.stderr += (
            process_idx + "\n" if idx > 0 else "" + process.stderr
        )

        if show_args_used:
            print(process_idx + process.args)

        if print_output:
            if format_output:
                print(process_idx + combined_process.stdout)
            else:
                print(process_idx + combined_process.stdout)
            if combined_process.stderr:
                if raise_on_stderr:
                    raise Exception(process_idx + combined_process.stderr)
                if format_output:
                    print(process_idx + combined_process.stderr)
                else:
                    print(process_idx + combined_process.stderr)

            if combined_process.returncode > 0:
                if raise_on_exit_code:
                    raise Exception(
                        process_idx
                        + f"exit code {combined_process.returncode} "
                        + combined_process.stderr
                    )
                if format_output:
                    print(
                        process_idx
                        + f"exit code {combined_process.returncode} "
                        + combined_process.stderr
                    )
                else:
                    print(
                        process_idx
                        + f"exit code {combined_process.returncode} "
                        + combined_process.stderr
                    )
        else:
            if combined_process.stderr and raise_on_stderr:
                raise Exception(process_idx + combined_process.stderr)
            elif combined_process.returncode > 0 and raise_on_exit_code:
                raise Exception(
                    process_idx
                    + f"exit code {combined_process.returncode} "
                    + combined_process.stderr
                )

    return combined_process


if __name__ == "__main__":
    print("Rebuilding...")
    build()
    print("Complete!")
    # check_tailwind()
