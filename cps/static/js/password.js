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
        if ($('#password').data("verify") === "True") {
            // Initialized and ready to go
            var options = {};
            options.common = {
                minChar: $('#password').data("min"),
                maxChar: -1
            }
            options.ui = {
                bootstrap3: true,
                showProgressBar: false,
                showErrors: true,
                showVerdicts: false,
            }
            options.rules= {
                specialCharClass: "(?=.*?[^\\p{Letter}\\s0-9])",
                activated: {
                    wordNotEmail: false,
                    wordMinLength: $('#password').data("min"),
                    wordSimilarToUsername: false,
                    wordSequences: false,
                    wordTwoCharacterClasses: false,
                    wordRepetitions: false,
                    wordLowercase: $('#password').data("lower") === "True" ? true : false,
                    wordUppercase: $('#password').data("upper") === "True" ? true : false,
                    word: $('#password').data("word") === "True" ? true : false,
                    wordOneNumber: $('#password').data("number") === "True" ? true : false,
                    wordThreeNumbers: false,
                    wordOneSpecialChar: $('#password').data("special") === "True" ? true : false,
                    wordUpperLowerCombo: false,
                    wordLetterNumberCombo: false,
                    wordLetterNumberCharCombo: false
                }
            }
            $('#password').pwstrength(options);
        }
    });
});
