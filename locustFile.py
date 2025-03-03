from locust import HttpUser, task, between

class CalibreUser(HttpUser):
    wait_time = between(1, 3)  # Simulate human-like delays



    @task
    def view_book_details(self):
        self.client.get("/book/5")  # Replace with a valid book ID

    @task
    def view_download(self):
        self.client.get("/download/stored/")

    @task
    def view_download(self):
        self.client.get("/newest/zyx/")
