/* This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
 *    Copyright (C) 2022  OzzieIsaacs
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program. If not, see <http://www.gnu.org/licenses/>.
 */
$(document).ready(function() {
    i18next.use(i18nextHttpBackend).init({
        lng: $('#password').data("lang"),
        debug: false,
        fallbackLng: 'en',
          backend: {
              loadPath: getPath() + "/static/js/libs/pwstrength/locales/{{lng}}.json",
          },

        }, function () {
        if ($('#password').data("verify")) {
            // Initialized and ready to go
            var options = {};
            options.common = {
                minChar: $('#password').data("min")
            }
            options.ui = {
                bootstrap3: true,
                showProgressBar: false,
                showErrors: true,
                showVerdicts: false,
            }
            options.rules= {
                activated: {
                    wordNotEmail: false,
                    wordMinLength: $('#password').data("min") ? true : false,
                    // wordMaxLength: false,
                    // wordInvalidChar: true,
                    wordSimilarToUsername: false,
                    wordSequences: false,
                    wordTwoCharacterClasses: false,
                    wordRepetitions: false,
                    wordLowercase: $('#password').data("lower") ? true : false,
                    wordUppercase: $('#password').data("upper") ? true : false,
                    wordOneNumber: $('#password').data("number") ? true : false,
                    wordThreeNumbers: false,
                    wordOneSpecialChar: $('#password').data("special") ? true : false,
                    // wordTwoSpecialChar: true,
                    wordUpperLowerCombo: false,
                    wordLetterNumberCombo: false,
                    wordLetterNumberCharCombo: false
                }
            }
            $('#password').pwstrength(options);
        }
    });
});
