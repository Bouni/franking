<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { type Settings, useAppStore } from "@/store/app";

const TRACKING_LINK = "{tracking_link}";

const store = useAppStore();
const { isLoading, settings } = storeToRefs(store);
const { fetchSettings, saveSettings } = store;

const form = ref<Settings>({
  tracking_email_enabled: true,
  tracking_email_subject: "",
  tracking_email_body: "",
});

watch(
  settings,
  (s) => {
    if (s) {
      form.value = {
        tracking_email_enabled: s.tracking_email_enabled,
        tracking_email_subject: s.tracking_email_subject,
        tracking_email_body: s.tracking_email_body,
      };
    }
  },
  { immediate: true },
);

onMounted(fetchSettings);

const placeholders = computed(
  () => settings.value?.tracking_placeholders ?? {},
);
const linkMissing = computed(
  () => !form.value.tracking_email_body.includes(TRACKING_LINK),
);

// Placeholders are inserted at the cursor of the field that was focused last
type Field = "tracking_email_subject" | "tracking_email_body";
const lastField = ref<Field>("tracking_email_body");
const subjectField = ref();
const bodyField = ref();

async function insert(placeholder: string) {
  const field = lastField.value;
  const component =
    field === "tracking_email_subject" ? subjectField.value : bodyField.value;
  const input: HTMLInputElement | HTMLTextAreaElement | null =
    component?.$el.querySelector("input, textarea");
  const text = form.value[field];
  const start = input?.selectionStart ?? text.length;
  const end = input?.selectionEnd ?? text.length;
  form.value[field] = text.slice(0, start) + placeholder + text.slice(end);
  await nextTick();
  input?.focus();
  input?.setSelectionRange(
    start + placeholder.length,
    start + placeholder.length,
  );
}
</script>

<template>
  <v-row>
    <v-col cols="12" lg="8">
      <v-card
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

          <v-text-field
            ref="subjectField"
            v-model="form.tracking_email_subject"
            class="mt-4"
            label="Subject"
            @focus="lastField = 'tracking_email_subject'"
          />

          <v-textarea
            ref="bodyField"
            v-model="form.tracking_email_body"
            auto-grow
            :error-messages="
              linkMissing ? `The text must contain ${TRACKING_LINK}` : []
            "
            label="Text"
            rows="12"
            @focus="lastField = 'tracking_email_body'"
          />

          <div class="text-caption mb-2">
            Placeholders, click to insert at the cursor:
          </div>

          <div class="d-flex flex-wrap ga-2">
            <v-tooltip
              v-for="(description, placeholder) in placeholders"
              :key="placeholder"
              location="top"
              :text="description"
            >
              <template #activator="{ props: tooltipProps }">
                <v-chip
                  v-bind="tooltipProps"
                  :color="placeholder === TRACKING_LINK ? 'primary' : undefined"
                  label
                  @click="insert(placeholder)"
                >
                  {{ placeholder }}
                </v-chip>
              </template>
            </v-tooltip>
          </div>
        </v-card-text>

        <v-card-actions>
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
        </v-card-actions>
      </v-card>
    </v-col>
  </v-row>
</template>
