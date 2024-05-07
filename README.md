# Merchant Scroll

Merchant Scroll is a personal Python project for Magic: the Gathering that formats a Moxfield collection export CSV file for Card Kingdom's Sell List CSV import tool. The script minimizes how many cards the CSV import tool fails to identify by applying Card Kingdom's card name formatting to the Moxfield CSV file. 

## Card Kingdom Card Name Formatting
For select cards, Card Kingdom appends collector number and other text to card names. Wizards of the Coast changed collector number digits from 3 to 4 with March of the Machine (MOM) so Card Kingdom format is 'card name (###)' for sets before and 'card name (####)' for sets after.

### Basic Lands
* Card Kingdom appends collector number to basic land card names
* Card Kingdom appends an additional letter to basic lands for sets prior to Ikoria: Lair of Behemoths (IKO) if the set includes multiple basic lands of the same type  
* Card Kingdom appends letters in alphabetical order from least to greatest collector number for basic lands of the same type in the same set

### Tokens
* Card Kingdom appends 'Token' to token card names
* Card Kingdom additionally appends collector number to token card names if the set includes multiple token cards with the same name

### Bonus Sheets
* Enchanting Tales (WOT), the Wilds of Eldraine bonus sheet - Card Kingdom appends collector number to the card name
* Breaking News (OTP), the Outlaws of Thunder Junction bonus sheet - Card Kingdom appends collector number and 'Showcase' to the card name  

___
This project is named after the [Merchant Scroll](https://scryfall.com/card/hml/33/merchant-scroll) card

![There's no trade without trust](https://www.mtgnexus.com/img/gallery/1689731076/4443-merchant-scroll.jpg)
