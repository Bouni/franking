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
        </v-tabs-window>
      </v-container>
    </v-main>
  </v-app>
</template>

<script lang="ts" setup>
import { ref } from "vue";
import Invoices from "@/components/Invoices.vue";
import OrderForm from "@/components/Orderform.vue";

const tab = ref("invoices");
</script>
