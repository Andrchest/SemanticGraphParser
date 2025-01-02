# Function defined outside of any class
def global_function(message):
    return f"This is a function defined outside of any class: {message}"

# Nested function defined outside of any class
def outer_function(greeting):
    def inner_function(name):
        return f"{greeting}, {name}! This is an inner function defined within outer_function."

    return inner_function("Alice")

# Class defined in the global scope
class OuterClass:
    def __init__(self, name):
        self.name = name

    # Function defined in the class
    def greet(self, greeting):
        return f"{greeting}, {self.name}!"

    # Function defined in a method
    def create_inner_class(self, inner_message):
        # Class defined in the function
        class InnerClass:
            def __init__(self, message):
                self.message = message

            # Function defined in the class
            def display_message(self):
                return f"Inner message: {self.message}"

            # Function defined in another method of InnerClass
            def create_deep_inner_class(self, detail):
                # Class defined within InnerClass
                class DeepInnerClass:
                    def __init__(self, detail):
                        self.detail = detail

                    # Function defined in DeepInnerClass
                    def show_detail(self):
                        return f"Detail from DeepInnerClass: {self.detail}"

                # Create an instance of DeepInnerClass
                deep_inner_instance = DeepInnerClass(detail)
                return deep_inner_instance.show_detail()

        # Create an instance of InnerClass
        inner_instance = InnerClass(inner_message)
        return inner_instance.display_message(), inner_instance.create_deep_inner_class("This is a deep inner class detail.")

# Example usage
if __name__ == "__main__":
    # Using the global function
    print(global_function("Hello from global function!"))

    # Using the nested function
    print(outer_function("Greetings"))

    # Using the OuterClass
    outer_instance = OuterClass("Alice")
    print(outer_instance.greet("Hi"))

    # Using the InnerClass through OuterClass
    inner_message, deep_inner_detail = outer_instance.create_inner_class("This is an inner class message.")
    print(inner_message)
    print(deep_inner_detail)