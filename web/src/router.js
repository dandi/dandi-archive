import Vue from 'vue';
import Router from 'vue-router';
import Home from './views/Home.vue';
import DandiMetaViewer from '@/views/DandiMetaViewer.vue';

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
      path: '/:_modelType?/:_id?',
      name: 'home',
      component: Home,
    },
    {
      path: '/:_modelType?/:_id/selected/:ids+',
      name: 'home2',
      component: Home,
    },
  ],
});
