import Vue from 'vue';
import Router from 'vue-router';
Vue.use(Router);

export default new Router({
  mode: 'history',
  routes: [
    { 
      path: '/',
      name: 'HomePage',
      component: () => import('../views/HomePage.vue')
    },
    {
      path: '/plant-details/:speciesName',
      name: 'PlantDetails',
      component: () => import('../views/PlantDetails.vue'),
      props: true
    },
    {
      path: '/upload-data',
      name: 'UploadData',
      component: () => import('../views/UploadData.vue')
    },
  ]
});
