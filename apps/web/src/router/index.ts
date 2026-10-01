import { createRouter, createWebHistory } from 'vue-router';

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/dashboard', component: () => import('@/views/DashboardView.vue'), meta: { title: 'Dashboard' } },
    { path: '/observations', component: () => import('@/views/ObservationsView.vue'), meta: { title: 'Observations' } },
    { path: '/alerts', component: () => import('@/views/AlertsView.vue'), meta: { title: 'Alertes' } },
    { path: '/locations', component: () => import('@/views/LocationsView.vue'), meta: { title: 'Localisations' } },
  ],
});
