<script setup lang="ts">
import { computed, nextTick, ref } from "vue";

const props = defineProps<{
  placeholders: Record<string, string>;
  // Placeholder the text must contain, highlighted in the list
  required?: string;
}>();

const subject = defineModel<string>("subject", { required: true });
const body = defineModel<string>("body", { required: true });

const missing = computed(
  () => !!props.required && !body.value.includes(props.required),
);

// Placeholders are inserted at the cursor of the field that was focused last
type Field = "subject" | "body";
const lastField = ref<Field>("body");
const subjectField = ref();
const bodyField = ref();

async function insert(placeholder: string) {
  const field = lastField.value === "subject" ? subject : body;
  const component =
    lastField.value === "subject" ? subjectField.value : bodyField.value;
  const input: HTMLInputElement | HTMLTextAreaElement | null =
    component?.$el.querySelector("input, textarea");
  const text = field.value;
  const start = input?.selectionStart ?? text.length;
  const end = input?.selectionEnd ?? text.length;
  field.value = text.slice(0, start) + placeholder + text.slice(end);
  await nextTick();
  input?.focus();
  input?.setSelectionRange(
    start + placeholder.length,
    start + placeholder.length,
  );
}
</script>

<template>
  <v-text-field
    ref="subjectField"
    v-model="subject"
    class="mt-4"
    label="Subject"
    @focus="lastField = 'subject'"
  />

  <v-textarea
    ref="bodyField"
    v-model="body"
    auto-grow
    :error-messages="missing ? `The text must contain ${required}` : []"
    label="Text"
    rows="12"
    @focus="lastField = 'body'"
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
          :color="placeholder === required ? 'primary' : undefined"
          label
          @click="insert(placeholder)"
        >
          {{ placeholder }}
        </v-chip>
      </template>
    </v-tooltip>
  </div>
</template>
