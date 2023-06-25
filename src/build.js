import * as fs from 'fs/promises';
import { get } from 'http';

const wpAPIBasePath = 'http://admin.innerpathllc.com/wp-json/wp/v2';

async function build() {
    // TODO: move static to public folder

    const menu = await wpGetAll('menu');
    const navArray = menu.map((menuItem) => {
        const itemUrlParts = menuItem.url.split('/');
        const navItem = {
            wpID: menuItem.ID,
            name: menuItem.title,
            parentWpID: parseInt(menuItem.menu_item_parent),
            sortOrder: menuItem.menu_order,
            targetSlug:
                menuItem.url[menuItem.url.length - 1] === '/'
                    ? itemUrlParts[itemUrlParts.length - 2]
                    : itemUrlParts[itemUrlParts.length - 1]
        };
        if (navItem.name === 'Home') navItem.targetSlug = '/';
        return navItem;
    });

    const anchors = [];
    const parentItems = navArray
        .filter((item) => item.parentWpID === 0)
        .map((parent) => {
            parent.children = navArray.filter(
                (child) => child.parentWpID === parent.wpID
            );
            if (parent.children.length) {
                anchors.push({ id: parent.wpID, el: null });
            }
            return parent;
        });

    const parentMenu = parentItems
        .sort((a, b) => a.sortOrder - b.sortOrder)
        .map((item, i) => {
            let submenu = null;
            if (item.children.length) {
                const anchor = anchors.find((el) => el.id === item.wpID);
                submenu = `<ul>${item.children
                    .sort((a, b) => a.sortOrder - b.sortOrder)
                    .map(
                        (child, i) =>
                            `<a href=/pages/${child.targetSlug}.html>${child.name}</a>`
                    )}<ul>`;
            }
            return `<div>${submenu}</div>`;
        })
        .concat(' ');

    const pages = await wpGetAll('pages');
    const layout = await fs.readFile('src/layout.html', { encoding: 'utf-8' });

    const pagesTasks = pages.map((page) => {
        const isIndex = page.title.rendered === 'Home';

        if (!page.status === 'publish') return Promise.resolve();

        return fs.writeFile(
            isIndex ? 'public/index.html' : `public/pages/${page.slug}.html`,
            layout
                .replace('{{nav}}', parentMenu)
                .replace('{{title}}', page.title.rendered)
                .replace('{{contents}}', page.content.rendered)
        );
    });
    await Promise.all(pagesTasks);
}

async function wpGetAll(url, queryParams) {
    let wpRes = [];
    let curResLength = 0;
    let curPage = 1;

    // If we get 100 results, loop until it's less so we get everything
    do {
        const wpResPage = await nodeGet(
            `${wpAPIBasePath}/${url}?per_page=100&page=${curPage}`
        );

        wpRes = wpRes.concat(wpResPage);
        curResLength = wpResPage.length;
        curPage++;
    } while (curResLength === 100);
    console.log(wpRes);
    return wpRes;
}

async function nodeGet(url) {
    let p = new Promise((resolve, reject) => {
        get(url, (res) => {
            const { statusCode } = res;
            const contentType = res.headers['content-type'];

            let error;
            // Any 2xx status code signals a successful response but
            // here we're only checking for 200.
            if (statusCode !== 200) {
                error = new Error(
                    'Request Failed.\n' + `Status Code: ${statusCode}`
                );
            } else if (!/^application\/json/.test(contentType)) {
                error = new Error(
                    'Invalid content-type.\n' +
                        `Expected application/json but received ${contentType}`
                );
            }
            if (error) {
                console.error(error.message);
                // Consume response data to free up memory
                res.resume();
                return;
            }

            res.setEncoding('utf8');
            let rawData = '';
            res.on('data', (chunk) => {
                rawData += chunk;
            });
            res.on('end', () => {
                try {
                    const parsedData = JSON.parse(rawData);
                    resolve(parsedData);
                } catch (e) {
                    console.error(e.message);
                }
            });
        }).on('error', (e) => {
            reject(e.message);
        });
    });
    return p;
}

build();
