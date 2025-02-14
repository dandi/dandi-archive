/**
 * plugins/vuetify.ts
 *
 * Framework documentation: https://vuetifyjs.com`
 */

// Styles
import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'
import colors from 'vuetify/util/colors';

// Composables
import { createVuetify } from 'vuetify'

const DandiLightTheme = {
  dark: false,
  colors: {
    primary: colors.lightBlue.darken1,
    secondary: colors.blueGrey.base,
    accent: colors.lightBlue.darken1,
    error: colors.red.base,
    info: colors.lightBlue.lighten1,
    dropzone: colors.grey.lighten3,
    highlight: colors.yellow.lighten4,
  }
};

const DandiDarkTheme = {
  dark: true,
  colors: {
    primary: colors.lightBlue.darken3,
    secondary: colors.grey.base,
    accent: colors.lightBlue.lighten1,
    dropzone: colors.grey.darken2,
    highlight: colors.grey.darken2,
  }
};

// https://vuetifyjs.com/en/introduction/why-vuetify/#feature-guides
export default createVuetify({
  // Use Girder web components theme
  // https://github.com/girder/girder_web_components/blob/master/src/utils/vuetifyConfig.js
  theme: {
    defaultTheme: 'DandiLightTheme',
    themes: {
      DandiLightTheme,
      DandiDarkTheme,
    },
  },
  icons: {
    defaultSet: 'mdi',
    aliases: {
      alert: 'mdi-alert-circle',
      bitbucket: 'mdi-bitbucket',
      box_com: 'mdi-package',
      chevron: 'mdi-chevron-right',
      circle: 'mdi-checkbox-blank-circle',
      collection: 'mdi-file-tree',
      download: 'mdi-download',
      edit: 'mdi-pencil',
      externalLink: 'mdi-open-in-new',
      file: 'mdi-file',
      fileMultiple: 'mdi-file-multiple',
      fileNew: 'mdi-file-plus',
      fileUpload: 'mdi-file-upload',
      folder: 'mdi-folder',
      folderNonPublic: 'mdi-folder-key',
      folderNew: 'mdi-folder-plus',
      github: 'mdi-github-circle',
      globe: 'mdi-earth',
      globus: 'mdi-earth',
      google: 'mdi-google',
      group: 'mdi-account-multiple',
      item: 'mdi-file',
      linkedin: 'mdi-linkedin',
      lock: 'mdi-lock',
      login: 'mdi-login',
      logout: 'mdi-logout',
      more: 'mdi-dots-horizontal',
      otp: 'mdi-shield-key',
      preview: 'mdi-file-find',
      search: 'mdi-magnify',
      settings: 'mdi-tune',
      user: 'mdi-account',
      userHome: 'mdi-home-account',
      view: 'mdi-eye',
    },
  },
});
