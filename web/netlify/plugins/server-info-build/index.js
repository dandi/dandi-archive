/* eslint-disable no-console */
const https = require('https');
const fs = require('fs');
const path = require('path');

module.exports = {
  // Use onPostBuild hook so that the dist/ folder exists
  onPostBuild: async ({ constants }) => {
    let apiUrl = process.env.VUE_APP_DANDI_API_ROOT;
    if (apiUrl === undefined) {
      throw new Error('API URL not defined. Please define it with the VUE_APP_DANDI_API_ROOT environment variable.');
    }

    apiUrl = apiUrl.endsWith('/') ? apiUrl.slice(0, -1) : apiUrl;
    await new Promise((resolve, reject) => {
      https.get(`${apiUrl}/info/`, (res) => {
        res.on('data', (d) => {
          const filepath = path.join(process.cwd(), constants.PUBLISH_DIR, 'server-info.json');
          const parsed = JSON.parse(d.toString());
          const formatted = JSON.stringify(parsed, null, 2);

          // Write file and resolve promise.
          console.log(`Writing ${filepath}...`);
          fs.writeFileSync(filepath, Buffer.from(formatted));
          resolve();
        });
      }).on('error', (e) => {
        // Log error and reject promise. Build will be aborted.
        console.error(e);
        reject(e);
      });
    });
  },
};
