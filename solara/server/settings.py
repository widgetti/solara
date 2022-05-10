import pydantic


class Main(pydantic.BaseConfig):
    use_pdb: bool = False


main = Main()
