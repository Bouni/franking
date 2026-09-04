<template>
  <v-app>
    <v-main>
      <v-container fluid>
        <v-app-bar>
          <v-app-bar-title>Franking</v-app-bar-title>
        </v-app-bar>
        <Invoices />
      </v-container>
    </v-main>
  </v-app>
</template>

<script lang="ts" setup>
import Invoices from "@/components/Invoices.vue";
</script>
