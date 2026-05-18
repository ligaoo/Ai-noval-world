import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Dropdown from 'primevue/dropdown'
import Card from 'primevue/card'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import Dialog from 'primevue/dialog'
import Divider from 'primevue/divider'
import Badge from 'primevue/badge'
import ProgressBar from 'primevue/progressbar'
import Toast from 'primevue/toast'
import ToastService from 'primevue/toastservice'
import Tooltip from 'primevue/tooltip'

import App from './App.vue'
import router from './router'
import 'primevue/resources/themes/lara-dark-purple/theme.css'
import './assets/main.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(PrimeVue, { ripple: true })
app.use(ToastService)

// 注册全局组件
app.component('PButton', Button)
app.component('PInputText', InputText)
app.component('PTextarea', Textarea)
app.component('PDropdown', Dropdown)
app.component('PCard', Card)
app.component('PTabView', TabView)
app.component('PTabPanel', TabPanel)
app.component('PDialog', Dialog)
app.component('PDivider', Divider)
app.component('PBadge', Badge)
app.component('PProgressBar', ProgressBar)
app.component('PToast', Toast)

// 全局指令
app.directive('tooltip', Tooltip)

app.mount('#app')
