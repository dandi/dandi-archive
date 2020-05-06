import { CLIENT_URL, uniqueId, registerNewUser } from '../util';
import {
  vBtn,
  vTextField,
  vTextarea,
  vCard,
  vChip,
} from '../vuetify-xpaths';


describe('dandiset registration page', () => {
  beforeAll(async () => {
    await page.goto(CLIENT_URL);
  });

  it('registers a new dandiset', async () => {
    const id = uniqueId();
    const name = `name ${id}`;
    const description = `description ${id}`;

    await registerNewUser();

    await expect(page).toClickXPath(vBtn('New Dandiset'));

    await expect(page).toFillXPath(vTextField('Name*'), name);
    await expect(page).toFillXPath(vTextarea('Description*'), description);

    await expect(page).toClickXPath(vBtn('Register dataset'));

    await expect(page).toContainXPath(vCard({ title: [name, vChip('This dataset has not been published!')] }));
  });
});
