window.onload = setup

let menuOpen = false;

function setup() {
    console.log('Test!');
    let menuButton = document.getElementById('user-menu-button');
    let menu = document.getElementById('user-menu');
    menuButton.onclick = () => {
        menuOpen = !menuOpen
        if (menuOpen) {
            menu.classList.remove('hidden');
        } else {
            menu.classList.add('hidden')
        }
    };
    menuButton.onmouseenter = () => {
        if (menuOpen) return;
        menuOpen = true;
        menu.classList.remove('hidden');
    }

    menu.onmouseleave = () => {
        if (!menuOpen) return;
        menuOpen = false;
        menu.classList.add('hidden')
    }
}