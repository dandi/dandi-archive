export default {
  // Use onPostBuild hook so that the dist/ folder exists
  onPostBuild: ({ netlifyConfig }) => {
    let apiUrl = process.env.VITE_APP_DANDI_API_ROOT;
    if (apiUrl === undefined) {
      throw new Error('API URL not defined. Please define it with the VITE_APP_DANDI_API_ROOT environment variable.');
    }

    // Add redirect to server info
    apiUrl = apiUrl.endsWith('/') ? apiUrl.slice(0, -1) : apiUrl;
    netlifyConfig.redirects.unshift({
      from: '/server-info',
      to: `${apiUrl}/info/?format=json`,
      status: 200,
    });
  },
};
