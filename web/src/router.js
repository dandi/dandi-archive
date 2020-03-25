import Vue from 'vue';
import Router from 'vue-router';

import HomeView from '@/views/HomeView/HomeView.vue';
import PublicDandisetsView from '@/views/PublicDandisetsView/PublicDandisetsView.vue';
import MyDandisetsView from '@/views/MyDandisetsView/MyDandisetsView.vue';
import DandisetLandingView from '@/views/DandisetLandingView/DandisetLandingView.vue';

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
      path: '/dandiset/:id',
      name: 'dandisetLanding',
      props: true,
      component: DandisetLandingView,
    },
  ],
});
