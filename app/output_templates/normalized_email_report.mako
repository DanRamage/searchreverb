<!DOCTYPE html>

<html lang="en">
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.6.1/dist/css/bootstrap.min.css" integrity="sha384-zCbKRCUGaJDkqS1kPbPd7TveP5iyJE0EjAuZQTgFLD2ylzuqKfdKlfG/eSrtxUkn" crossorigin="anonymous">
      <title>Reverb Items</title>
    </head>
    <body>
        <!--
        -->
        <div class="container">
            <div class="row">
                <div class="col-sm-12">
                    <h3>Search Results for ${user}</h3>
                </div>
            </div>
            <div class="row">
                <div class="col-sm-12">
                    <h3>Search Term: ${search_rec.search_item}</h3>
                </div>
            </div>
            <div class="row">
                <div class="col-sm-12">
                    <h3>Max Price: ${search_rec.max_price} Min Price: ${search_rec.min_price}</h3>
                </div>
            </div>
            <div class="row">
                <div class="col-sm-12">
                    <h3>${search_execute_time}</h3>
                </div>
            </div>
            <div class="row">
                <div class="col-sm-12">
                    <h3>These are the matches found based on your search string and want price.</h3>
                </div>
            </div>
            </br>
            <div class="row">
              % for result in search_results:
                <table class="table table-striped table-bordered">
                    <tr>
                        <th>Item</th>
                        <th>Condition</th>
                        <th>Price</th>
                        <th>Link</th>
                    </tr>
                    % for page_ndx,listing in enumerate(result):
                      <tr>
                        <td>
                          ${str(listing.listing_description)}
                        </td>
                        <td>
                          ${str(listing.condition)}
                        </td>
                        <td>
                          ${listing.price}
                        </td>
                        <td>
                          <a href="${listing.link}">Link</a>
                        </td>
                      </tr>
                    % endfor
                </table>
              % endfor
            </div>
        </div>
    </body>
</html>
