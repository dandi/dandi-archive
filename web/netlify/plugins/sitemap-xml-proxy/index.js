export default {
  // Use onPostBuild hook so that the dist/ folder exists
  onPostBuild: ({ netlifyConfig }) => {
    let backendUrl = process.env.VITE_APP_DANDI_BACKEND_ROOT;
    if (backendUrl === undefined) {
      throw new Error('BACKEND URL not defined. Please define it with the VITE_APP_DANDI_BACKEND_ROOT environment variable.');
    }

    // Add redirect to sitemap view
    backendUrl = backendUrl.endsWith('/') ? backendUrl.slice(0, -1) : backendUrl;
    netlifyConfig.redirects.unshift({
      from: '/sitemap.xml',
      to: `${backendUrl}/sitemaps/frontend.xml`,
      status: 200,
    });
  },
};
