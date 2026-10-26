import prettier from "eslint-config-prettier";
import vuetify from "eslint-config-vuetify";

// Formatting is handled by Prettier, eslint-config-prettier turns off all
// rules that would conflict with it
export default vuetify(
  {
    stylistic: false,
    ignore: { extendIgnore: ["public", ".vite"] },
  },
  prettier,
);
