require(['gitbook', 'jquery'], function(gitbook, $) {
    // Configuration
    var MAX_SIZE       = 4,
        MIN_SIZE       = 0,
        MAX_WIDE       = 1600,
        MIN_WIDE       = 800,
        STEP_WIDE      = 80,
        BUTTON_ID;

    // Current fontsettings state
    var fontState;

    // Default themes
    var THEMES = [
        {
            config: 'white',
            text: 'White',
            id: 0
        },
        {
            config: 'sepia',
            text: 'Sepia',
            id: 1
        },
        /*{
            config: 'night',
            text: 'Night',
            id: 2
        },*/
        {
            config: 'green',
            text: 'Green',
            id: 3
        }
    ];

    // Default font families
    var FAMILIES = [
        {
            config: 'serif',
            text: 'Serif',
            id: 0
        },
        {
            config: 'sans',
            text: 'Sans',
            id: 1
        }
    ];

    // Return configured themes
    function getThemes() {
        return THEMES;
    }

    // Modify configured themes
    function setThemes(themes) {
        THEMES = themes;
        updateButtons();
    }

    // Return configured font families
    function getFamilies() {
        return FAMILIES;
    }

    // Modify configured font families
    function setFamilies(families) {
        FAMILIES = families;
        updateButtons();
    }

    // Save current font settings
    function saveFontSettings() {
        gitbook.storage.set('fontState', fontState);
        update();
    }

    // Increase font size
    function enlargeFontSize(e) {
        e.preventDefault();
        if (fontState.size >= MAX_SIZE) return;

        fontState.size++;
        saveFontSettings();
    }

    // Decrease font size
    function reduceFontSize(e) {
        e.preventDefault();
        if (fontState.size <= MIN_SIZE) return;

        fontState.size--;
        saveFontSettings();
    }

    // Increase page wide
    function increaseWide(e) {
        e.preventDefault();
        if (fontState.wide >= MAX_WIDE) return;

        fontState.wide = fontState.wide + STEP_WIDE;
        console.log('in wide' + fontState.wide)
        saveFontSettings();
    }

    // Decrease page wide
    function decreaseWide(e) {
        e.preventDefault();
        if (fontState.wide <= MIN_WIDE) return;

        fontState.wide = fontState.wide - STEP_WIDE;
        console.log('de wide' + fontState.wide)
        saveFontSettings();
    }

    // Change font family
    function changeFontFamily(configName, e) {
        if (e && e instanceof Event) {
            e.preventDefault();
        }

        var familyId = getFontFamilyId(configName);
        fontState.family = familyId;
        saveFontSettings();
    }

    // Change type of color theme
    function changeColorTheme(configName, e) {
        if (e && e instanceof Event) {
            e.preventDefault();
        }

        var $book = gitbook.state.$book;

        // Remove currently applied color theme
        if (fontState.theme !== 0)
            $book.removeClass('color-theme-'+fontState.theme);

        // Set new color theme
        var themeId = getThemeId(configName);
        fontState.theme = themeId;
        if (fontState.theme !== 0)
            $book.addClass('color-theme-'+fontState.theme);

        saveFontSettings();
    }

    // Return the correct id for a font-family config key
    // Default to first font-family
    function getFontFamilyId(configName) {
        // Search for plugin configured font family
        var configFamily = $.grep(FAMILIES, function(family) {
            return family.config == configName;
        })[0];
        // Fallback to default font family
        return (!!configFamily)? configFamily.id : 0;
    }

    // Return the correct id for a theme config key
    // Default to first theme
    function getThemeId(configName) {
        // Search for plugin configured theme
        var configTheme = $.grep(THEMES, function(theme) {
            return theme.config == configName;
        })[0];
        // Fallback to default theme
        return (!!configTheme)? configTheme.id : 0;
    }

    function update() {
        var $book = gitbook.state.$book;

        $('.font-settings .font-family-list li').removeClass('active');
        $('.font-settings .font-family-list li:nth-child('+(fontState.family+1)+')').addClass('active');

        $book[0].className = $book[0].className.replace(/\bfont-\S+/g, '');
        $book.addClass('font-size-'+fontState.size);
        $book.addClass('font-family-'+fontState.family);

        if(fontState.theme !== 0) {
            $book[0].className = $book[0].className.replace(/\bcolor-theme-\S+/g, '');
            $book.addClass('color-theme-'+fontState.theme);
        }
        console.log(fontState.wide);
        wide = fontState.wide || 800;
        $('.page-inner').css( "maxWidth", wide);
    }

    function init(config) {
        // Search for plugin configured font family
        var configFamily = getFontFamilyId(config.family),
            configTheme = getThemeId(config.theme);

        // Instantiate font state object
        fontState = gitbook.storage.get('fontState', {
            size:   config.size || 2,
            wide:   config.wide || 800,
            family: configFamily,
            theme:  configTheme
        });

        update();
    }

    function updateButtons() {
        // Remove existing fontsettings buttons
        if (!!BUTTON_ID) {
            gitbook.toolbar.removeButton(BUTTON_ID);
        }

        // Create buttons in toolbar
        BUTTON_ID = gitbook.toolbar.createButton({
            icon: 'fa fa-font',
            label: 'Font Settings',
            className: 'font-settings',
            dropdown: [
                [
                    {
                        text: 'A',
                        className: 'font-reduce',
                        onClick: reduceFontSize
                    },
                    {
                        text: 'A',
                        className: 'font-enlarge',
                        onClick: enlargeFontSize
                    }
                ],
                [
                    {
                        text: 'Narrow',
                        //className: 'font-enlarge',
                        onClick: decreaseWide
                    },
                    {
                        text: 'Wide',
                        //className: 'font-enlarge',
                        onClick: increaseWide
                    }
                ],
                $.map(FAMILIES, function(family) {
                    family.onClick = function(e) {
                        return changeFontFamily(family.config, e);
                    };

                    return family;
                }),
                $.map(THEMES, function(theme) {
                    theme.onClick = function(e) {
                        return changeColorTheme(theme.config, e);
                    };

                    return theme;
                })
            ]
        });
    }

    gitbook.toolbar.createButton({
        icon: 'fa fa-search',
        onClick: function(e) {
            //e.preventDefault();
            console.log(1);
            gitbook.sidebar.toggle();
        }
    });

    // Init configuration at start
    gitbook.events.bind('start', function(e, config) {
        var opts = config.fontsettings;

        // Generate buttons at start
        updateButtons();

        // Init current settings
        init(opts);
    });

    gitbook.events.on('page.change', function() {
        update();
    });

    // Expose API
    gitbook.fontsettings = {
        decreaseWide:    decreaseWide,
        increaseWide:    increaseWide,
        enlargeFontSize: enlargeFontSize,
        reduceFontSize:  reduceFontSize,
        setTheme:        changeColorTheme,
        setFamily:       changeFontFamily,
        getThemes:       getThemes,
        setThemes:       setThemes,
        getFamilies:     getFamilies,
        setFamilies:     setFamilies
    };
});