<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, ref, watch } from "vue";
import EmailTemplate from "@/components/EmailTemplate.vue";
import { type Settings, useAppStore } from "@/store/app";

const TRACKING_LINK = "{tracking_link}";

const store = useAppStore();
const { isLoading, settings } = storeToRefs(store);
const { fetchSettings, saveSettings } = store;

const form = ref<Settings>({
  invoice_email_subject: "",
  invoice_email_body: "",
  tracking_email_enabled: true,
  tracking_email_subject: "",
  tracking_email_body: "",
});

watch(
  settings,
  (s) => {
    if (s) {
      form.value = {
        invoice_email_subject: s.invoice_email_subject,
        invoice_email_body: s.invoice_email_body,
        tracking_email_enabled: s.tracking_email_enabled,
        tracking_email_subject: s.tracking_email_subject,
        tracking_email_body: s.tracking_email_body,
      };
    }
  },
  { immediate: true },
);

onMounted(fetchSettings);

const linkMissing = computed(
  () => !form.value.tracking_email_body.includes(TRACKING_LINK),
);
</script>

<template>
  <v-row>
    <v-col cols="12" lg="8">
      <v-card
        :loading="isLoading?.action === 'fetchSettings'"
        prepend-icon="mdi-email-arrow-right"
        subtitle="Sent to the customer with the invoice PDF attached"
        title="Invoice email"
      >
        <v-card-text>
          <EmailTemplate
            v-model:body="form.invoice_email_body"
            v-model:subject="form.invoice_email_subject"
            :placeholders="settings?.invoice_placeholders ?? {}"
          />
        </v-card-text>
      </v-card>

      <v-card
        class="mt-4"
        :loading="isLoading?.action === 'fetchSettings'"
        prepend-icon="mdi-email-fast"
        subtitle="Sent to the customer when a Sendcloud label is created"
        title="Tracking email"
      >
        <v-card-text>
          <v-switch
            v-model="form.tracking_email_enabled"
            color="primary"
            hide-details
            label="Send the tracking link to the customer"
          />

          <EmailTemplate
            v-model:body="form.tracking_email_body"
            v-model:subject="form.tracking_email_subject"
            :placeholders="settings?.tracking_placeholders ?? {}"
            :required="TRACKING_LINK"
          />
        </v-card-text>
      </v-card>

      <div class="d-flex mt-4">
        <v-spacer />

        <v-btn
          color="primary"
          :disabled="linkMissing"
          :loading="isLoading?.action === 'saveSettings'"
          variant="flat"
          @click="saveSettings(form)"
        >
          Save
        </v-btn>
      </div>
    </v-col>
  </v-row>
</template>
