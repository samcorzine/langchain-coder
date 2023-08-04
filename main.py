from langchain.llms import OpenAI
import os
from typing import Optional


def get_code(file_path: str) -> str:
    with open(file_path, "r") as f:
        return f.read()

def swap_code(file_path: str, code: str) -> None:
    # Swap the code in a file with the code provided
    os.remove(file_path)
    with open(file_path, "w") as f:
        f.write(code)

def build_go_package(project_directory: str) -> Optional[str]:
    # Build a go package from a directory
    import subprocess

    try:
        # Run the command and capture the output
        output = subprocess.check_output('go build -o bin/', shell=True, stderr=subprocess.STDOUT, cwd=project_directory)
        print(output.decode('utf-8'))
    except subprocess.CalledProcessError as e:
        # Handle the error
        return e.output.decode('utf-8')

class Coder:
    def __init__(self, client: OpenAI):
        self.client: OpenAI = client
        self.boiler = """
        You are a very experienced developer and you have been given a software project that you need to make updates to.
        I will provide you with a high-level description of the project, as well as the entirety of the code for one file in the codebase.
        You will only be able to see the code for the file that I provide you with, but you can assume that the rest of the codebase works correctly and that the functions its using are defined elsewhere
        """

    def plan_prompt(self, project_directory: str, file: str) -> str:
        project_structure = describe_directory_structure(project_directory)
        code = get_code(file)
        return f"""{self.boiler}
        I'd like to improve the error handling in the code below. Please write a plan for how you would refactor the code to improve the error handling.
            
        Directory Structure:
        
        {project_structure}
        
        Code:
        
        {code}
        """

    def refactor_prompt(self, project_directory: str, file: str, plan: str) -> str:
        project_structure = describe_directory_structure(project_directory)
        code = get_code(file)
        return f"""{self.boiler}
        Please refactor the code below. Output the entire file so that I can replace the existing file with it. 
        DO NOT output any text that isn't part of the new file, I'd like to directly copy the output you give me.
        Rememeber to output fully working code, and I will test it to make sure it works, but don't omit anything.
        Also don't include backticks in your output.
        
        
        Directory Structure:
        {project_structure}
        Code:
        {code}
        Plan:
        {plan}
        
        Your code:
        """

    def broken_file_prompt(self, project_directory: str, file: str, output: str) -> str:
        project_structure = describe_directory_structure(project_directory)
        code = get_code(file)
        return f"""{self.boiler}
        
        I've tried to build the project after replacing my file with the code you gave me, but it failed. Please fix the code so that the project builds successfully.
        Output only the corrected code and no additional text!
        
        Directory Structure:
        {project_structure}
        Code:
        {code}
        Build Output:
        {output}
        """

    def build_plan_and_refactor(self, project_directory: str, file: str):
        # Build a plan for refactoring a file
        plan = self.client(prompt=self.plan_prompt(project_directory, file))
        print(plan)

        refactor_prompt = self.refactor_prompt(project_directory, file, plan)
        new_code = self.client(prompt=refactor_prompt)
        swap_code(file, new_code)

        output = build_go_package(project_directory)
        if not output:
            return
        print(f"First errors: {output}")
        latest_code = get_code(file_path)
        broken_file_prompt = self.broken_file_prompt(project_directory, file, output)
        new_code = self.client(prompt=broken_file_prompt)
        swap_code(file, new_code)




def describe_directory_structure(directory: str) -> str:
    # Print a nested description of a directory with file names
    # and subdirectories with their file names and so on
    # EX:
    # - main.py
    # - test.py
    # - utils/
    #   - __init__.py
    #   - utils.py
    #  ...

    # Filter out hidden files
    prompt = f"""
{directory}
Files:
    """
    for root, dirs, files in os.walk(directory):
        level = root.replace(directory, "").count(os.sep)
        indent = " " * 4 * (level)
        prompt += f"{indent}{os.path.basename(root)}/\n"
        subindent = " " * 4 * (level + 1)
        for f in files:
            if f.startswith(".") or f.endswith(".pyc"):
                continue
            prompt += f"{subindent}{f}\n"
    return prompt


if __name__ == "__main__":
    llm = OpenAI(model_name="gpt-3.5-turbo", verbose=True)
    file_path = "/Users/samcorzine/playground/wiseml/wiseml-server/container.go"
    directory = "/Users/samcorzine/playground/wiseml/wiseml-server/"
    coder = Coder(llm)
    coder.build_plan_and_refactor(directory, file_path)
    print(build_go_package(directory))








