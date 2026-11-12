const standardSidebar = document.getElementById("scnd-nav");

if (standardSidebar) {
    const desktopNavigation = document.querySelector(".sidebar-column .navigation");
    const mainNavigation = document.getElementById("main-nav");
    const desktopViewport = window.matchMedia("(min-width: 768px)");

    function positionStandardSidebar() {
        standardSidebar.classList.toggle("nav", !desktopViewport.matches);
        standardSidebar.classList.toggle("navbar-nav", !desktopViewport.matches);
        if (desktopViewport.matches) {
            desktopNavigation.append(standardSidebar);
        } else {
            mainNavigation.after(standardSidebar);
        }
    }

    desktopViewport.addEventListener("change", positionStandardSidebar);
    positionStandardSidebar();
}
