<template>
  <v-app>
    <v-main>
      <v-container fluid>
        <v-app-bar>
          <img :src="Avatar" width="64" height="64" class="ml-2" alt="" />
          <v-app-bar-title> BSH Board order</v-app-bar-title>
        </v-app-bar>
        <OrderForm />
      </v-container>
    </v-main>
  </v-app>
</template>

<script lang="ts" setup>
import Avatar from "@/assets/avatar.svg";
import OrderForm from "@/components/Orderform.vue";
</script>
