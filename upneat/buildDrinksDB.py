import re

from sqlalchemy import create_engine, Column, String, Integer, Table, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import IntegrityError
import logging.handlers

logging.basicConfig(level=logging.INFO)
engine = create_engine('sqlite:///drinks.db')

Base = declarative_base()

ing_assc_table = Table('ing_assc', Base.metadata,
                       Column('Drink_name', String, ForeignKey('drinks.drink_name')),
                       Column('Ingredients_string', String, ForeignKey('ingredients.ing_id')))


gar_assc_table = Table('gar_assc', Base.metadata,
                       Column('Drink_name', String, ForeignKey('drinks.drink_name')),
                       Column('Garnish_string', String, ForeignKey('garnishes.gar')))

class Drink(Base):
    __tablename__ = 'drinks'

    drink_name = Column(String, primary_key=True)
    source = Column(String)

    ingredients = relationship("Ingredient", secondary = ing_assc_table)
    garnishes = relationship("Garnish", secondary = gar_assc_table)

    def __repr__(self):
        return "<Drink(drink_name = {}, page = {})>".format(self.drink_name, self.page)

class Ingredient(Base):
    __tablename__ = 'ingredients'
    # Make ing the primary key, will hold all ingredients
    ing_id = Column(Integer, primary_key=True)
    ing = Column(String)
    quantity = Column(Float)
    measurement = Column(String)
    popularity = Column(Integer)

    drinks = relationship("Drink", secondary = ing_assc_table)
    simple_ing = Column(String, ForeignKey('simple.ing'))
    simple = relationship("Simple_Drink", backref = 'ingredients', uselist = True)
    # This relationship allows for simplification of ingredient names. Used for Inventory purposes
    # simple_name = relationship("Simple_Drink", backref = Simple_Drink)

    def __repr__(self):
        return "<Ingredient(ing = {}, quantity = {}, measurement = {}, popularity = {})>".format(
            self.ing, self.quantity, self.measurement, self.popularity)

class Garnish(Base):
    __tablename__ = 'garnishes'
    # holds garnishes for each drink. This may or may not work with relationships
    gar = Column(String, primary_key=True)

    def __repr__(self):
        return "<Garnish(gar = {})>".format(self.gar)

class Simple_Drink(Base):
    __tablename__ = 'simple'

    ing = Column(String, primary_key= True)

    # Intended to count how many ingredients match to this simplification. Not currently implemented
    population = Column(Integer)

    def __repr__(self):
        return "<Simple_Drink(ing = {}, population = {})>".format(self.ing, self.population)

Session = sessionmaker(bind=engine, autoflush= False)
Base.metadata.create_all(engine)

class DB_Builder():
    def __init__(self):
        self.session = Session()
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.DEBUG)
    def verify_ing_for_inv(self, ing_name):
        """
        Compares ing_name vs values in both ingredients table and simple table
        :param ing_name: a String that holds the ingredient name to be added
        :param session: a drinks.db Session() object
        :return: ingredient name if one exists, otherwise empty string
        """

        ingredients_check = self.session.query(Ingredient).filter(Ingredient.ing.like(ing_name)).first()
        simple_ing_check = self.session.query(Simple_Drink).filter(Simple_Drink.ing.like(ing_name)).first()
        if ingredients_check:
            # if ing_name matches an Ingredient in the table, return that Ingredient's name
            return ingredients_check.ing
        elif simple_ing_check:
            # if ing_name matches a Simple_Drink in the table, return that Simple_Drink's ingredient name
            return simple_ing_check.ing
        else:
            # If neither matches, return an empty string. This will be checked against in the calling function
            return ""

    def simplify_ingredient(self, ingredient):
        """Takes an ingredient object and returns its simplified name if available, otherwise returns full ingredient name
        Always returns uppercase text."""
        if ingredient.simple_ing:
            return ingredient.simple_ing.upper()
        else:
            return ingredient.ing.upper()

    def query_drink_contains(self, name):

        return self.session.query(Drink).filter(Drink.drink_name.contains(name)).all()

    def query_drink_all(self, name):

        return self.session.query(Drink).filter(Drink.drink_name.like(name)).all()

    def query_drink_first(self, name):

        return self.session.query(Drink).filter(Drink.drink_name.like(name)).first()

    def add_ingredient(self, quantity, measurement, ingredient):

        new_ing = Ingredient(quantity=quantity, measurement=measurement, ing=ingredient, popularity=0)
        self.session.add(new_ing)
        self.log.info("Adding new Ingredient {}".format(new_ing))
        try:
            self.session.commit()
            return new_ing
        except:
            self.session.rollback()
            self.log.error("Trying to add duplicate values to Ingredient, returning empty string")
            # querys the existing ingredient and returns it so that drink doesn't get empty string
            return self.session.query(Ingredient).filter(Ingredient.ing == ingredient, Ingredient.quantity == quantity,
                                                Ingredient.measurement == measurement).first()

    def add_drink(self, name, source):
        """Try to add a new drink to the Drink database, return Drink object and session"""
        try:
            new_drink = Drink(drink_name=name, source=source)
            # Add our Drink object to our Session
            self.session.add(new_drink)
            # Commit the changes to the database
            self.session.commit()
            return new_drink
        except IntegrityError as e:
            print("Trying to add a non-unique row to database")
            raise

    def check_garnish_in_table(self, garnish):
        in_table = self.session.query(Garnish).filter(Garnish.gar == garnish).first()

        if not in_table:
            self.log.info("Adding garnish {} to table".format(garnish))
            gar = Garnish(gar=garnish)
        else:
            self.log.debug("Garnish already in table")
            gar = in_table
        return gar

    def ing_regex(self, ing_name):
        """
        Uses regex to separate quantity from ingredients
        :param ingredient: ingredient name from spreadsheet (eg. 2 DASHES ANGOSTURA BITTERS)
        :return: Returns three variables: quantity (float), measurement (String), ing (String)
        """
        # Initialize holder variables
        quantity, measurement = "", ""

        # Num pattern looks for numbers and periods at start of string, plus a space after
        num_pattern = r"^[1-9.]+ "
        match_num = re.match(num_pattern, ing_name)

        # If ing_name has a number at start of string, proceed
        if match_num:
            # Cast quantity in string to float
            quantity = float(match_num.group().strip())
            # Remove this number substring from ing_name
            ing_name = re.sub(num_pattern, "", ing_name)

        # Move on to checking for corner case values (TSP, DASHES, etc.)
        # These can be done simultaneously because they are mutually exclusive
        patterns = [r"^DASH[E]*[S]* ", r"^TSP[S]* ", r"^TEASPOON[S]* ", r"^BARSPOON[S]* ", r"^OUNCE[S]* ", r"^oz[.]* "]

        # Make a regex that matches if any of our regexes match.
        comb_pattern = "(" + ")|(".join(patterns) + ")"

        match = re.match(comb_pattern, ing_name, flags=re.IGNORECASE)


        #
        # match_dash = re.match(dash_pattern, ing_name,flags = re.IGNORECASE)
        # match_tsp = re.match(tsp_pattern, ing_name, flags = re.IGNORECASE)
        # match_barspoon = re.match(barspoon, ing_name, flags = re.IGNORECASE)
        if match:
            measurement = match.group().strip()
            ing_name = re.sub(measurement, "", ing_name, flags=re.IGNORECASE)

        # elif match_tsp:
        #     measurement = match_tsp.group().strip()
        #     ing_name = re.sub(measurement, "", ing_name)
        # elif match_barspoon:
        #     measurement = match_barspoon.group().strip()
        #     ing_name = re.sub(measurement, "", ing_name)
        # # For special cases, there will be no measurement given (Egg, Mint, etc)
        # elif re.match(r"(MINT )+(EGG )+(FUJI )+(RIPE )+", ing_name, flags = re.IGNORECASE):
        #     # measurement remains blank if it's a special case
        #     measurement = ""
        # elif re.match(r"^oz\. ", ing_name, flags = re.IGNORECASE):
        #     measurement = "oz."
        #     ing_name = re.sub(measurement, "", ing_name)

        ing_name = ing_name . strip()
        # self.log.addHandler(logging.handlers.RotatingFileHandler)

        if "ounce" in ing_name.lower():
            raise ValueError("Dammit, there's still a problem here")

        self.log.debug("ING_NAME IS==={}\n\n\n".format(ing_name))

        #First value
        # If no number matched, set quantity to zero (arbitrary number), else return quantity
        if not quantity:
            quantity = 0

        return quantity, measurement, ing_name

