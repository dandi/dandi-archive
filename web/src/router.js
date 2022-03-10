import Vue from 'vue';
import Router from 'vue-router';
import FileBrowser from '@/views/FileBrowserView/FileBrowser.vue';

import HomeView from '@/views/HomeView/HomeView.vue';
import PublicDandisetsView from '@/views/PublicDandisetsView/PublicDandisetsView.vue';
import MyDandisetsView from '@/views/MyDandisetsView/MyDandisetsView.vue';
import SearchDandisetsView from '@/views/SearchDandisetsView/SearchDandisetsView.vue';
import DandisetLandingView from '@/views/DandisetLandingView/DandisetLandingView.vue';
import CreateDandisetView from '@/views/CreateDandisetView/CreateDandisetView.vue';

Vue.use(Router);

export default new Router({
  routes: [
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
  ],
});
