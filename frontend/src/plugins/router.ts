import { createRouter, createWebHistory } from "vue-router";
import Dashboard from "../pages/Dashboard.vue";
import Order from "../pages/Order.vue";

const routes = [
  {
    path: "/",
    name: "dashboard",
    component: Dashboard,
    meta: { title: "Franking" },
  },
  {
    path: "/order",
    name: "order",
    component: Order,
    meta: { title: "BSH-Board" },
  },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

router.beforeEach((to, from, next) => {
  // Use route meta title or fall back to a default app title
  const DEFAULT_TITLE = "";
  document.title = to.meta.title || DEFAULT_TITLE;
  next();
});

export default router;
