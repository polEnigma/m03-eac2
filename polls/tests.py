from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


@override_settings(LANGUAGE_CODE="en-us")
class StaffPasswordTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Només l'administrador inicial es crea amb l'ORM.
        User.objects.create_superuser(
            username="isard",
            email="isard@example.com",
            password="pirineus",
        )

        options = Options()
        options.add_argument("-headless")
        cls.browser = webdriver.Firefox(options=options)
        cls.addClassCleanup(cls.browser.quit)
        cls.browser.set_window_size(1280, 1000)

    def setUp(self):
        self.wait = WebDriverWait(self.browser, 15)

    def field(self, element_id, value):
        element = self.wait.until(
            EC.visibility_of_element_located((By.ID, element_id))
        )
        element.clear()
        element.send_keys(value)

    def login(self, username, password):
        self.browser.get(self.live_server_url + "/admin/")
        self.field("id_username", username)
        self.field("id_password", password)
        self.browser.find_element(
            By.CSS_SELECTOR, 'input[type="submit"]'
        ).click()
        self.wait.until(
            EC.presence_of_element_located((By.ID, "logout-form"))
        )
        self.assertIn(
            username.lower(),
            self.browser.find_element(By.ID, "user-tools").text.lower(),
        )

    def test_staff_password_validators(self):
        staff_user = "staff_eac2"
        initial_password = "Roca!Violeta_72Mar"

        # Crear l'usuari mitjançant el formulari de Django admin.
        self.login("isard", "pirineus")
        self.browser.get(self.live_server_url + "/admin/auth/user/add/")
        self.field("id_username", staff_user)
        self.field("id_password1", initial_password)
        self.field("id_password2", initial_password)
        self.browser.find_element(By.NAME, "_continue").click()

        staff_checkbox = self.wait.until(
            EC.presence_of_element_located((By.ID, "id_is_staff"))
        )
        if not staff_checkbox.is_selected():
            staff_checkbox.click()

        self.assertTrue(staff_checkbox.is_selected())
        self.assertFalse(
            self.browser.find_element(By.ID, "id_is_superuser").is_selected()
        )
        self.browser.find_element(By.NAME, "_save").click()
        self.wait.until(
            EC.url_to_be(self.live_server_url + "/admin/auth/user/")
        )

        # Tornar a obrir l'usuari per verificar que staff s'ha desat.
        self.browser.find_element(By.LINK_TEXT, staff_user).click()
        self.assertTrue(
            self.wait.until(
                EC.presence_of_element_located((By.ID, "id_is_staff"))
            ).is_selected()
        )
        self.assertFalse(
            self.browser.find_element(By.ID, "id_is_superuser").is_selected()
        )

        # Tancar la sessió d'administrador i entrar com a staff.
        self.browser.find_element(
            By.CSS_SELECTOR, "#logout-form button"
        ).click()
        self.wait.until(
            EC.presence_of_element_located((By.LINK_TEXT, "Log in again"))
        )
        self.login(staff_user, initial_password)

        cases = [
            ("similaritat", staff_user,
             "The password is too similar to the username."),
            ("longitud", "qZ!7",
             "This password is too short. It must contain at least 8 characters."),
            ("comuna", "password",
             "This password is too common."),
            ("numerica", "938572640183",
             "This password is entirely numeric."),
        ]

        # Provocar i comprovar cadascun dels quatre errors.
        for name, invalid_password, expected_error in cases:
            with self.subTest(restriction=name):
                self.browser.get(
                    self.live_server_url + "/admin/password_change/"
                )
                self.field("id_old_password", initial_password)
                self.field("id_new_password1", invalid_password)
                self.field("id_new_password2", invalid_password)
                self.browser.find_element(
                    By.CSS_SELECTOR, 'input[type="submit"]'
                ).click()

                self.wait.until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, ".errorlist")
                    )
                )
                errors = "\n".join(
                    element.text for element in self.browser.find_elements(
                        By.CSS_SELECTOR, ".errorlist"
                    )
                )
                self.assertIn(expected_error, errors)
                self.assertTrue(
                    self.browser.current_url.endswith("/admin/password_change/")
                )
                print(f"OK restriccio {name}: {expected_error}", flush=True)

        # Comprovar també que una contrasenya segura sí que s'accepta.
        self.browser.get(self.live_server_url + "/admin/password_change/")
        self.field("id_old_password", initial_password)
        self.field("id_new_password1", "Bosc!Turquesa_93Sol")
        self.field("id_new_password2", "Bosc!Turquesa_93Sol")
        self.browser.find_element(
            By.CSS_SELECTOR, 'input[type="submit"]'
        ).click()
        self.wait.until(
            EC.url_to_be(
                self.live_server_url + "/admin/password_change/done/"
            )
        )
        self.assertIn(
            "Your password was changed.",
            self.browser.find_element(By.TAG_NAME, "body").text,
        )
