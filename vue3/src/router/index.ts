import { createRouter, createWebHistory } from 'vue-router'

import HomeView from '@/views/HomeView/HomeView.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/dandiset',
      name: 'publicDandisets',
      component: () => import('../views/PublicDandisetsView/PublicDandisetsView.vue'),
    },
    {
      path: '/dandiset/my',
      name: 'myDandisets',
      component: () => import('../views/MyDandisetsView/MyDandisetsView.vue'),
    },
    {
      path: '/dandiset/search',
      name: 'searchDandisets',
      component: () => import('../views/SearchDandisetsView/SearchDandisetsView.vue'),
    },
    {
      path: '/dandiset/create',
      name: 'createDandiset',
      component: () => import('../views/CreateDandisetView/CreateDandisetView.vue'),
    },
    {
      path: '/dandiset/:identifier/:version/files',
      name: 'fileBrowser',
      props: true,
      component: () => import('../views/FileBrowserView/FileBrowser.vue'),
    },
    {
      path: '/dandiset/:identifier/:version?',
      name: 'dandisetLanding',
      props: true,
      component: () => import('../views/DandisetLandingView/DandisetLandingView.vue'),
    },
    {
      path: '/search',
      name: 'search',
      component: () => import('../views/SearchView/SearchView.vue'),
    },
  ]
})

export default router;
