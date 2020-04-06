import Vue from 'vue';
import Router from 'vue-router';
import Home from './views/Home.vue';
import DandiMetaViewer from '@/views/DandiMetaViewer.vue';
import FileBrowser from '@/views/FileBrowser.vue';

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
      path: '/file-browser/:_modelType?/:_id?',
      name: 'file-browser',
      component: FileBrowser,
    },
    {
      path: '/',
      name: 'home',
      component: Home,
    },
  ],
});
