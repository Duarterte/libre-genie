// nav selection: mark the li whose anchor matches the current path
(function () {
    function setSelectedForPath(path) {
        const items = document.querySelectorAll('.top-nav > li');
        items.forEach(li => li.classList.remove('selected'));
        const anchors = document.querySelectorAll('.top-nav > li > a');
        anchors.forEach(a => {
            try {
                const url = new URL(a.href, location.href);
                if (url.pathname === path) a.parentElement.classList.add('selected');
            } catch (e) { /* ignore malformed */ }
        });
    }
    document.addEventListener('DOMContentLoaded', () => setSelectedForPath(location.pathname));
    // update selection on click (helps SPA navigation)
    document.querySelectorAll('.top-nav > li > a').forEach(a => {
        a.addEventListener('click', (e) => {
            // set selection immediately; navigation may follow
            const li = a.parentElement;
            document.querySelectorAll('.top-nav > li').forEach(x => x.classList.remove('selected'));
            li.classList.add('selected');
        });
    });
})();