import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import numbro from "numbro";

import en from '../../locales/en.json';
import sv from '../../locales/sv.json';
import fi from '../../locales/fi.json';

import numbroSv from 'numbro/dist/languages/sv-SE.min.js';
import numbroFi from 'numbro/dist/languages/fi-FI.min.js';


// the translations
// (tip move them in a JSON file and import them,
// or even better, manage them separated from your code: https://react.i18next.com/guides/multiple-translation-files)
const resources = {
  en: {
    translation: en,
  },
  sv: {
    translation: sv,
  },
  fi: {
    translation: fi,
  }
};

i18n
  .use(initReactI18next) // passes i18n down to react-i18next
  .init({
    resources,
    lng: 'fi',
    interpolation: {
      escapeValue: false // react already safes from xss
    }
  });


numbro.registerLanguage({
  ...numbroFi,
  languageTag: 'fi',
});

numbro.registerLanguage({
  ...numbroSv,
  languageTag: 'sv',
});

export default i18n;
