<template>
  <v-row>
    <v-col cols="12" lg="6">
      <v-card title="Info">
        <v-card-text>
          You're about to order a BSH Board, so let me clarify a few things.
          <ul>
            <li>
              This is a side project for me, so I have no interest in setting up
              a real webshop for it. Therefore I created this little order form
              to help me process orders more conveniently.
            </li>
            <li>
              Once you placed an order, I'll manually send you an invoice.
            </li>
            <li>I only send out invoices if I have boards available.</li>
            <li>
              Once you paid the invoice, I usually ship the next business day.
            </li>
          </ul>
        </v-card-text>
      </v-card>
    </v-col>
    <v-col cols="12" lg="6">
      <v-card title="FAQ">
        <v-card-text>
          <v-row>
            <v-col cols="12" lg="6">
              <v-card variant="tonal">
                <v-card-text>
                  <div class="mb-2">
                    <v-icon icon="mdi-chat-question" /> What connector type do I
                    need?
                  </div>
                  <div>
                    <v-icon icon="mdi-chat-alert" /> You need one 3-pin RAST
                    connector for the board itself. You will also need a 3-pin
                    or a 4-pin RAST connector for the machine side. Which one
                    depends on your model but there is definitiv list which
                    model needs which connector.
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
            <v-col cols="12" lg="6">
              <v-card variant="tonal">
                <v-card-text>
                  <div class="mb-2">
                    <v-icon icon="mdi-chat-question" /> Can you sell me ready to
                    use RAST connection cables?
                  </div>
                  <div>
                    <v-icon icon="mdi-chat-alert" /> Unfortunately, no. Not at
                    this point, maybe I can in the future but there are no plans
                    for this now. For me 3x0.34mm² cable worked out pretty well.
                    Alternatively you can use single wires of this size.
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </v-col>
    <v-col cols="12" lg="2" class="d-none d-lg-block"> </v-col>
    <v-col cols="12" lg="8">
      <v-card class="pa-5">
        <v-form ref="form" v-model="isFormValid" @submit.prevent="handleSubmit">
          <v-card title="Adress data" variant="outlined" class="pa-4 mb-3">
            <v-row density="compact">
              <v-col cols="12" lg="6">
                <v-text-field
                  v-model="order.firstname"
                  label="First Name"
                  hint="* Required field"
                  persistent-hint
                  :rules="[rules.required]"
                ></v-text-field>
              </v-col>

              <v-col cols="12" lg="6">
                <v-text-field
                  v-model="order.lastname"
                  label="Last Name"
                  hint="* Required field"
                  persistent-hint
                  :rules="[rules.required]"
                ></v-text-field>
              </v-col>

              <v-col cols="12" lg="6">
                <v-text-field
                  v-model="order.email"
                  label="Email Address"
                  hint="* Required field"
                  persistent-hint
                  :rules="[rules.required, rules.email]"
                ></v-text-field>
              </v-col>

              <v-col cols="12" lg="6"> </v-col>

              <v-col cols="12" lg="6">
                <v-text-field
                  v-model="order.address"
                  label="Address"
                  hint="* Required field"
                  persistent-hint
                  :rules="[rules.required]"
                ></v-text-field>
              </v-col>

              <v-col cols="12" lg="6">
                <v-text-field
                  v-model="order.city"
                  label="City"
                  hint="* Required field"
                  persistent-hint
                  :rules="[rules.required]"
                ></v-text-field>
              </v-col>

              <v-col cols="12" lg="6">
                <v-text-field
                  v-model="order.postalcode"
                  label="Postal code"
                  hint="* Required field"
                  persistent-hint
                  :rules="[rules.required]"
                ></v-text-field>
              </v-col>

              <v-col cols="12" lg="6">
                <v-autocomplete
                  v-model="order.country"
                  :items="COUNTRIES"
                  item-title="name"
                  item-value="code"
                  label="Select Country"
                  :rules="[rules.required]"
                  hint="* Required field"
                  persistent-hint
                  clearable
                >
                  <template #item="{ props, item }">
                    <v-list-item v-bind="props" :title="item.name">
                      <template #prepend>
                        <span
                          class="text-h6 mr-2"
                          :class="`fi fi-${item.code.toLowerCase()}`"
                          style="border-radius: 2px"
                        ></span>
                      </template>
                    </v-list-item>
                  </template>
                  <template #selection="{ item }">
                    <span
                      class="text-h6 mr-2"
                      :class="`fi fi-${order.country.toLowerCase()}`"
                      style="border-radius: 2px"
                    ></span>
                    <span>{{ item.name }}</span>
                  </template>
                </v-autocomplete>
              </v-col>
            </v-row>
          </v-card>

          <v-card title="Items" variant="outlined" class="pa-4">
            <v-row
              v-for="item in order.items"
              key="item.article_number"
              density="compact"
            >
              <v-col cols="12" sm="6" lg="6">
                <div class="item-caption">{{ item.name }}</div>
              </v-col>
              <v-col cols="12" sm="2" lg="2">
                <div class="item-caption">{{ item.price.toFixed(2) }}€</div>
              </v-col>
              <v-col cols="12" sm="2" lg="2">
                <div class="item-caption">
                  {{ (item.quantity * item.price).toFixed(2) }}€
                </div>
              </v-col>
              <v-col cols="12" sm="2" lg="2">
                <v-text-field
                  v-model="item.quantity"
                  label="Quantity"
                  type="number"
                ></v-text-field>
              </v-col>
            </v-row>
            <v-row density="compact">
              <v-col cols="12" sm="6" lg="6">
                <div class="item-caption">Shipping</div>
              </v-col>
              <v-col cols="12" sm="2" lg="2"> </v-col>
              <v-col cols="12" sm="2" lg="2">
                <div class="item-caption">{{ shipping.toFixed(2) }}€</div>
              </v-col>
              <v-col cols="12" sm="2" lg="2"> </v-col>
            </v-row>
            <v-row density="compact">
              <v-col cols="12" sm="6" lg="6">
                <div class="item-caption">Sum</div>
              </v-col>
              <v-col cols="12" sm="2" lg="2"> </v-col>
              <v-col cols="12" sm="2" lg="2">
                <div class="item-caption">{{ grandTotal.toFixed(2) }}€</div>
              </v-col>
              <v-col cols="12" sm="2" lg="2"> </v-col>
            </v-row>
          </v-card>

          <v-row density="compact">
            <v-col cols="12" class="text-center">
              <v-btn type="submit" color="primary" class="mt-4">
                Submit Order
              </v-btn>
            </v-col>
          </v-row>
        </v-form>
      </v-card>
    </v-col>
    <v-col cols="12" lg="2" class="d-none d-lg-block"> </v-col>
  </v-row>
</template>

<style scoped>
.item-caption {
  background-color: #2a2a2a;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  height: 56px;
  line-height: 24px;
  padding-top: 15px;
  padding-left: 10px;
}
</style>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useOrderStore } from "@/store/order";
import { storeToRefs } from "pinia";
import { COUNTRIES, type Country } from "@/constants/countries";

const orderStore = useOrderStore();

const form = ref(null);
const isFormValid = ref(false);

const order = ref({
  firstname: "",
  lastname: "",
  email: "",
  address: "",
  city: "",
  postalcode: "",
  country: "",
  items: [
    { name: "BSH Board", article_number: "1", price: 15, quantity: 0 },
    {
      name: "RAST Connector 3-pin",
      article_number: "2",
      price: 1,
      quantity: 0,
    },
    {
      name: "RAST Connector 4-pin",
      article_number: "3",
      price: 1,
      quantity: 0,
    },
    { name: "BSH Board Case", article_number: "4", price: 10, quantity: 0 },
  ],
});

// Calculate subtotal for items only
const subtotal = computed(() => {
  return order.value.items.reduce((sum, item) => {
    return sum + item.price * item.quantity;
  }, 0);
});

const shipping = computed(() => {
  if (order.value.country == "") {
    return 0;
  } else if (order.value.country == "DE") {
    return 1.8;
  } else {
    return 3.3;
  }
});
// Calculate grand total including shipping
const grandTotal = computed(() => {
  return subtotal.value + shipping.value;
});

// Validation rules array of functions returning true or an error message string
const rules = {
  required: (val: unknown) => !!val || "This field is required.",
  email: (val: string) =>
    /.+@.+\..+/.test(val) || "Must be a valid email address.",
  minQuantity: (val: number) => val >= 1 || "Quantity must be at least 1.",
};

type FormInstance = {
  validate: () => Promise<{ valid: boolean }>;
};

const handleSubmit = async () => {
  const formRef = form.value as FormInstance | null;
  const { valid } = (await formRef?.validate()) ?? { valid: false };

  if (!valid) return;

  console.log("Order submitted successfully:", order);
};

onMounted(() => {
  orderStore.fetchProducts();
});
</script>
