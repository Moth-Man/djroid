class CrateService:
  def __init__(self, name: str, file_path: str, prompt: str):
    self.name = name
    self.file_path = file_path
    self.prompt = prompt

  def generate_crate(self):
    print(f"Generating crate {self.name} with prompt {self.prompt} and file path {self.file_path}")
    