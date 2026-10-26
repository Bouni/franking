/**
 * plugins/index.ts
 *
 * Automatically included in `./src/main.ts`
 */

// Types
import type { App } from "vue";

// Plugins
import pinia from "./pinia";
import router from "./router";
import vuetify from "./vuetify";

export function registerPlugins(app: App) {
  app.use(router);
  app.use(pinia);
  app.use(vuetify);
}
