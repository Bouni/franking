<template>
  <v-app>
    <v-main>
      <v-container fluid>
        <v-app-bar>
          <v-app-bar-title>Franking</v-app-bar-title>

          <template #extension>
            <v-tabs v-model="tab">
              <v-tab prepend-icon="mdi-file-document-multiple" value="invoices">
                Invoices
              </v-tab>

              <v-tab prepend-icon="mdi-cart" value="order">Order</v-tab>

              <v-tab prepend-icon="mdi-warehouse" value="stock">Stock</v-tab>

              <v-tab prepend-icon="mdi-cog" value="settings">Settings</v-tab>
            </v-tabs>
          </template>
        </v-app-bar>

        <v-tabs-window v-model="tab">
          <v-tabs-window-item value="invoices">
            <Invoices />
          </v-tabs-window-item>

          <v-tabs-window-item value="order">
            <OrderForm />
          </v-tabs-window-item>

          <v-tabs-window-item value="stock">
            <Stock />
          </v-tabs-window-item>

          <v-tabs-window-item value="settings">
            <Settings />
          </v-tabs-window-item>
        </v-tabs-window>

        <!-- Not reloaded automatically, that would drop a half filled form -->
        <v-snackbar :model-value="updateAvailable" :timeout="-1">
          A new version of Franking is available

          <template #actions>
            <v-btn color="primary" variant="text" @click="reload">Reload</v-btn>
          </template>
        </v-snackbar>
      </v-container>
    </v-main>
  </v-app>
</template>

<script lang="ts" setup>
import { storeToRefs } from "pinia";
import { ref } from "vue";
import Invoices from "@/components/Invoices.vue";
import OrderForm from "@/components/Orderform.vue";
import Settings from "@/components/Settings.vue";
import Stock from "@/components/Stock.vue";
import { useAppStore } from "@/store/app";

const { updateAvailable } = storeToRefs(useAppStore());

const tab = ref("invoices");

function reload() {
  location.reload();
}
</script>
