<template>
  <v-app>
    <v-main>
      <v-container fluid>
        <v-app-bar>
          <img alt="" class="ml-2" height="64" :src="Avatar" width="64" />

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
