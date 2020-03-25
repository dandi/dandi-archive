import Vue from 'vue';
import Router from 'vue-router';
import HomeView from '@/views/HomeView/HomeView.vue';
import DandiMetaViewer from '@/views/DandiMetaViewer/DandiMetaViewer.vue';

Vue.use(Router);

export default new Router({
  routes: [
    {
      path: '/dandiset-meta/:id',
      name: 'dandiset-metadata-viewer',
      props: true,
      component: DandiMetaViewer,
    },
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
  ],
});
