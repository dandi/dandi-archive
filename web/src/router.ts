import Vue from 'vue';
import Router, { RouteConfig } from 'vue-router';

import HomeView from '@/views/HomeView/HomeView.vue';
import PublicDandisetsView from '@/views/PublicDandisetsView/PublicDandisetsView.vue';
import MyDandisetsView from '@/views/MyDandisetsView/MyDandisetsView.vue';
import SearchDandisetsView from '@/views/SearchDandisetsView/SearchDandisetsView.vue';
import DandisetLandingView from '@/views/DandisetLandingView/DandisetLandingView.vue';
import CreateDandisetView from '@/views/CreateDandisetView/CreateDandisetView.vue';
import FileBrowser from '@/views/FileBrowserView/FileBrowser.vue';

Vue.use(Router);

const routes: RouteConfig[] = [
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
];

export default new Router({ routes });
