import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';

import HomeView from '@/views/HomeView/HomeView.vue';
import PublicDandisetsView from '@/views/PublicDandisetsView/PublicDandisetsView.vue';
import MyDandisetsView from '@/views/MyDandisetsView/MyDandisetsView.vue';
import SearchDandisetsView from '@/views/SearchDandisetsView/SearchDandisetsView.vue';
import DandisetLandingView from '@/views/DandisetLandingView/DandisetLandingView.vue';
import CreateDandisetView from '@/views/CreateDandisetView/CreateDandisetView.vue';
import FileBrowser from '@/views/FileBrowserView/FileBrowser.vue';
import SearchView from '@/views/SearchView/SearchView.vue';
import StarredDandisetsView from '@/views/StarredDandisetsView/StarredDandisetsView.vue';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: HomeView,
  },
  {
    path: '/dandiset',
    name: 'publicDandisets',
    component: PublicDandisetsView,
  },
  {
    path: '/dandiset/my',
    name: 'myDandisets',
    component: MyDandisetsView,
  },
  {
    path: '/dandiset/starred',
    name: 'starredDandisets',
    component: StarredDandisetsView,
    meta: {
      requiresAuth: true,
    },
  },
  {
    path: '/dandiset/search',
    name: 'searchDandisets',
    component: SearchDandisetsView,
  },
  {
    path: '/dandiset/create',
    name: 'createDandiset',
    component: CreateDandisetView,
  },
  {
    path: '/dandiset/:identifier/:version/files',
    name: 'fileBrowser',
    props: true,
    component: FileBrowser,
  },
  {
    path: '/dandiset/:identifier/:version?',
    name: 'dandisetLanding',
    props: true,
    component: DandisetLandingView,
  },
  {
    path: '/search',
    name: 'search',
    component: SearchView,
  },
];

// Listing-specific query params that must not appear on DLP URLs.
// Listing-specific params to strip from DLP URLs.
// Note: 'pos' and 'search' are intentionally NOT here — pos indicates position
// in a result set, and search populates the search bar for context.
const LISTING_PARAMS = ['page', 'sortOption', 'sortDir', 'showDrafts', 'showEmpty'];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// Safety net: strip leaked listing params from DLP routes.
router.beforeEach((to, _from, next) => {
  if (to.name === 'dandisetLanding') {
    const cleanQuery = { ...to.query };
    let modified = false;
    for (const param of LISTING_PARAMS) {
      if (param in cleanQuery) {
        delete cleanQuery[param];
        modified = true;
      }
    }
    if (modified) {
      next({ ...to, query: cleanQuery });
      return;
    }
  }
  next();
});

export default router;
