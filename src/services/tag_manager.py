class TagManager:
    def get_predefined_tags(self):
        return {
            "school": ["school::Riverdale", "school::Greenwood"],
            "grade": ["grade::Primary1", "grade::Primary2"],
            "term": ["term::Term1", "term::Term2"]
        }

    def get_user_tags(self, user_name: str):
        # Optional: Retrieve user-defined tags
        return []